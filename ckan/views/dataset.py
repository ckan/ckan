# encoding: utf-8
import logging
from collections import OrderedDict
from functools import partial
from six.moves.urllib.parse import urlencode
from datetime import datetime

from flask import Blueprint
from flask.views import MethodView
from werkzeug.datastructures import MultiDict
from ckan.common import asbool

import six
from six import string_types, text_type

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
import ckan.authz as authz
from ckan.common import _, config, g, request
from ckan.views.home import CACHE_PARAMETERS
from ckan.lib.plugins import lookup_package_plugin
from ckan.lib.render import TemplateNotFound
from ckan.lib.search import SearchError, SearchQueryError, SearchIndexError
from ckan.views import LazyView


NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

log = logging.getLogger(__name__)

dataset = Blueprint(
    u'dataset',
    __name__,
    url_prefix=u'/dataset',
    url_defaults={u'package_type': u'dataset'}
)


def _setup_template_variables(context, data_dict, package_type=None):
    return lookup_package_plugin(package_type).setup_template_variables(
        context, data_dict
    )


def _get_pkg_template(template_type, package_type=None):
    pkg_plugin = lookup_package_plugin(package_type)
    method = getattr(pkg_plugin, template_type)
    try:
        return method(package_type)
    except TypeError as err:
        if u'takes 1' not in str(err) and u'takes exactly 1' not in str(err):
            raise
        return method()


def _encode_params(params):
    return [(k, v.encode(u'utf-8') if isinstance(v, string_types) else str(v))
            for k, v in params]


def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)


def search_url(params, package_type=None):
    if not package_type:
        package_type = u'dataset'
    url = h.url_for(u'{0}.search'.format(package_type))
    return url_with_params(url, params)


def drill_down_url(alternative_url=None, **by):
    return h.add_url_param(
        alternative_url=alternative_url,
        controller=u'dataset',
        action=u'search',
        new_params=by
    )


def remove_field(package_type, key, value=None, replace=None):
    if not package_type:
        package_type = u'dataset'
    url = h.url_for(u'{0}.search'.format(package_type))
    return h.remove_url_param(
        key,
        value=value,
        replace=replace,
        alternative_url=url
    )


def _sort_by(params_nosort, package_type, fields):
    """Sort by the given list of fields.

    Each entry in the list is a 2-tuple: (fieldname, sort_order)
    eg - [(u'metadata_modified', u'desc'), (u'name', u'asc')]
    If fields is empty, then the default ordering is used.
    """
    params = params_nosort[:]

    if fields:
        sort_string = u', '.join(u'%s %s' % f for f in fields)
        params.append((u'sort', sort_string))
    return search_url(params, package_type)


def _pager_url(params_nopage, package_type, q=None, page=None):
    params = list(params_nopage)
    params.append((u'page', page))
    return search_url(params, package_type)


def _tag_string_to_list(tag_string):
    """This is used to change tags from a sting to a list of dicts.
    """
    out = []
    for tag in tag_string.split(u','):
        tag = tag.strip()
        if tag:
            out.append({u'name': tag, u'state': u'active'})
    return out


def _form_save_redirect(pkg_name, action, package_type=None):
    """This redirects the user to the CKAN package/read page,
    unless there is request parameter giving an alternate location,
    perhaps an external website.
    @param pkg_name - Name of the package just edited
    @param action - What the action of the edit was
    """
    assert action in (u'new', u'edit')
    url = request.args.get(u'return_to') or config.get(
        u'package_%s_return_url' % action
    )
    if url:
        url = url.replace(u'<NAME>', pkg_name)
    else:
        if not package_type:
            package_type = u'dataset'
        url = h.url_for(u'{0}.read'.format(package_type), id=pkg_name)
    return h.redirect_to(url)


def _get_package_type(id):
    """
    Given the id of a package this method will return the type of the
    package, or 'dataset' if no type is currently set
    """
    pkg = model.Package.get(id)
    if pkg:
        return pkg.type or u'dataset'
    return None


def _get_search_details():
    fq = u''

    # fields_grouped will contain a dict of params containing
    # a list of values eg {u'tags':[u'tag1', u'tag2']}

    fields = []
    fields_grouped = {}
    search_extras = MultiDict()

    for (param, value) in request.args.items(multi=True):
        if param not in [u'q', u'page', u'sort'] \
                and len(value) and not param.startswith(u'_'):
            if not param.startswith(u'ext_'):
                fields.append((param, value))
                fq += u' %s:"%s"' % (param, value)
                if param not in fields_grouped:
                    fields_grouped[param] = [value]
                else:
                    fields_grouped[param].append(value)
            else:
                search_extras.update({param: value})

    search_extras = dict([
        (k, v[0]) if len(v) == 1 else (k, v)
        for k, v in search_extras.lists()
    ])
    return {
        u'fields': fields,
        u'fields_grouped': fields_grouped,
        u'fq': fq,
        u'search_extras': search_extras,
    }


def search(package_type):
    extra_vars = {}

    try:
        context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        check_access(u'site_read', context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    # unicode format (decoded from utf8)
    extra_vars[u'q'] = q = request.args.get(u'q', u'')

    extra_vars['query_error'] = False
    page = h.get_page_number(request.args)

    limit = int(config.get(u'ckan.datasets_per_page', 20))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.args.items() if k != u'page']

    extra_vars[u'drill_down_url'] = drill_down_url
    extra_vars[u'remove_field'] = partial(remove_field, package_type)

    sort_by = request.args.get(u'sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != u'sort']

    extra_vars[u'sort_by'] = partial(_sort_by, params_nosort, package_type)

    if not sort_by:
        sort_by_fields = []
    else:
        sort_by_fields = [field.split()[0] for field in sort_by.split(u',')]
    extra_vars[u'sort_by_fields'] = sort_by_fields

    pager_url = partial(_pager_url, params_nopage, package_type)

    search_url_params = urlencode(_encode_params(params_nopage))
    extra_vars[u'search_url_params'] = search_url_params

    details = _get_search_details()
    extra_vars[u'fields'] = details[u'fields']
    extra_vars[u'fields_grouped'] = details[u'fields_grouped']
    fq = details[u'fq']
    search_extras = details[u'search_extras']

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }

    # Unless changed via config options, don't show other dataset
    # types any search page. Potential alternatives are do show them
    # on the default search page (dataset) or on one other search page
    search_all_type = config.get(u'ckan.search.show_all_types', u'dataset')
    search_all = False

    try:
        # If the "type" is set to True or False, convert to bool
        # and we know that no type was specified, so use traditional
        # behaviour of applying this only to dataset type
        search_all = asbool(search_all_type)
        search_all_type = u'dataset'
    # Otherwise we treat as a string representing a type
    except ValueError:
        search_all = True

    if not search_all or package_type != search_all_type:
        # Only show datasets of this particular type
        fq += u' +dataset_type:{type}'.format(type=package_type)

    facets = OrderedDict()

    org_label = h.humanize_entity_type(
        u'organization',
        h.default_group_type(u'organization'),
        u'facet label') or _(u'Organizations')

    group_label = h.humanize_entity_type(
        u'group',
        h.default_group_type(u'group'),
        u'facet label') or _(u'Groups')

    default_facet_titles = {
        u'organization': org_label,
        u'groups': group_label,
        u'tags': _(u'Tags'),
        u'res_format': _(u'Formats'),
        u'license_id': _(u'Licenses'),
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, package_type)

    extra_vars[u'facet_titles'] = facets
    data_dict = {
        u'q': q,
        u'fq': fq.strip(),
        u'facet.field': list(facets.keys()),
        u'rows': limit,
        u'start': (page - 1) * limit,
        u'sort': sort_by,
        u'extras': search_extras,
        u'include_private': asbool(
            config.get(u'ckan.search.default_include_private', True)
        ),
    }
    try:
        query = get_action(u'package_search')(context, data_dict)

        extra_vars[u'sort_by_selected'] = query[u'sort']

        extra_vars[u'page'] = h.Page(
            collection=query[u'results'],
            page=page,
            url=pager_url,
            item_count=query[u'count'],
            items_per_page=limit
        )
        extra_vars[u'search_facets'] = query[u'search_facets']
        extra_vars[u'page'].items = query[u'results']
    except SearchQueryError as se:
        # User's search parameters are invalid, in such a way that is not
        # achievable with the web interface, so return a proper error to
        # discourage spiders which are the main cause of this.
        log.info(u'Dataset search query rejected: %r', se.args)
        base.abort(
            400,
            _(u'Invalid search query: {error_message}')
            .format(error_message=str(se))
        )
    except SearchError as se:
        # May be bad input from the user, but may also be more serious like
        # bad code causing a SOLR syntax error, or a problem connecting to
        # SOLR
        log.error(u'Dataset search error: %r', se.args)
        extra_vars[u'query_error'] = True
        extra_vars[u'search_facets'] = {}
        extra_vars[u'page'] = h.Page(collection=[])

    # FIXME: try to avoid using global variables
    g.search_facets_limits = {}
    for facet in extra_vars[u'search_facets'].keys():
        try:
            limit = int(
                request.args.get(
                    u'_%s_limit' % facet,
                    int(config.get(u'search.facets.default', 10))
                )
            )
        except ValueError:
            base.abort(
                400,
                _(u'Parameter u"{parameter_name}" is not '
                  u'an integer').format(parameter_name=u'_%s_limit' % facet)
            )

        g.search_facets_limits[facet] = limit

    _setup_template_variables(context, {}, package_type=package_type)

    extra_vars[u'dataset_type'] = package_type

    # TODO: remove
    for key, value in six.iteritems(extra_vars):
        setattr(g, key, value)

    return base.render(
        _get_pkg_template(u'search_template', package_type), extra_vars
    )


def resources(package_type, id):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id, u'include_tracking': True}

    try:
        check_access(u'package_update', context, data_dict)
    except NotFound:
        return base.abort(404, _(u'Dataset not found'))
    except NotAuthorized:
        return base.abort(
            403,
            _(u'User %r not authorized to edit %s') % (g.user, id)
        )
    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Dataset not found'))

    package_type = pkg_dict[u'type'] or u'dataset'
    _setup_template_variables(context, {u'id': id}, package_type=package_type)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg

    return base.render(
        u'package/resources.html', {
            u'dataset_type': package_type,
            u'pkg_dict': pkg_dict,
            u'pkg': pkg
        }
    )


def read(package_type, id):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id, u'include_tracking': True}
    activity_id = request.params.get(u'activity_id')

    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Dataset not found'))

    g.pkg_dict = pkg_dict
    g.pkg = pkg
    # NB templates should not use g.pkg, because it takes no account of
    # activity_id

    if activity_id:
        # view an 'old' version of the package, as recorded in the
        # activity stream
        try:
            activity = get_action(u'activity_show')(
                context, {u'id': activity_id, u'include_data': True})
        except NotFound:
            base.abort(404, _(u'Activity not found'))
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to view activity data'))
        current_pkg = pkg_dict
        try:
            pkg_dict = activity[u'data'][u'package']
        except KeyError:
            base.abort(404, _(u'Dataset not found'))
        if u'id' not in pkg_dict or u'resources' not in pkg_dict:
            log.info(u'Attempt to view unmigrated or badly migrated dataset '
                     '{} {}'.format(id, activity_id))
            base.abort(404, _(u'The detail of this dataset activity is not '
                              'available'))
        if pkg_dict[u'id'] != current_pkg[u'id']:
            log.info(u'Mismatch between pkg id in activity and URL {} {}'
                     .format(pkg_dict[u'id'], current_pkg[u'id']))
            # the activity is not for the package in the URL - don't allow
            # misleading URLs as could be malicious
            base.abort(404, _(u'Activity not found'))
        # The name is used lots in the template for links, so fix it to be
        # the current one. It's not displayed to the user anyway.
        pkg_dict[u'name'] = current_pkg[u'name']

        # Earlier versions of CKAN only stored the package table in the
        # activity, so add a placeholder for resources, or the template
        # will crash.
        pkg_dict.setdefault(u'resources', [])

    # if the user specified a package id, redirect to the package name
    if data_dict['id'] == pkg_dict['id'] and \
            data_dict['id'] != pkg_dict['name']:
        return h.redirect_to(u'{}.read'.format(package_type),
                             id=pkg_dict['name'],
                             activity_id=activity_id)

    # can the resources be previewed?
    for resource in pkg_dict[u'resources']:
        resource_views = get_action(u'resource_view_list')(
            context, {
                u'id': resource[u'id']
            }
        )
        resource[u'has_views'] = len(resource_views) > 0

    package_type = pkg_dict[u'type'] or package_type
    _setup_template_variables(context, {u'id': id}, package_type=package_type)

    template = _get_pkg_template(u'read_template', package_type)
    try:
        return base.render(
            template, {
                u'dataset_type': package_type,
                u'pkg_dict': pkg_dict,
                u'pkg': pkg,  # NB deprecated - it is the current version of
                              # the dataset, so ignores activity_id
                u'is_activity_archive': bool(activity_id),
            }
        )
    except TemplateNotFound as e:
        msg = _(
            u"Viewing datasets of type \"{package_type}\" is "
            u"not supported ({file_!r}).".format(
                package_type=package_type, file_=e.message
            )
        )
        return base.abort(404, msg)

    assert False, u"We should never get here"


class CreateView(MethodView):
    def _is_save(self):
        return u'save' in request.form

    def _prepare(self, data=None):

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj,
            u'save': self._is_save()
        }
        try:
            check_access(u'package_create', context)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to create a package'))
        return context

    def post(self, package_type):
        # The staged add dataset used the new functionality when the dataset is
        # partially created so we need to know if we actually are updating or
        # this is a real new.
        context = self._prepare()
        is_an_update = False
        ckan_phase = request.form.get(u'_ckan_phase')
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        try:
            if ckan_phase:
                # prevent clearing of groups etc
                context[u'allow_partial_update'] = True
                # sort the tags
                if u'tag_string' in data_dict:
                    data_dict[u'tags'] = _tag_string_to_list(
                        data_dict[u'tag_string']
                    )
                if data_dict.get(u'pkg_name'):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict[u'id'] = data_dict[u'pkg_name']
                    del data_dict[u'pkg_name']
                    # don't change the dataset state
                    data_dict[u'state'] = u'draft'
                    # this is actually an edit not a save
                    pkg_dict = get_action(u'package_update')(
                        context, data_dict
                    )

                    # redirect to add dataset resources
                    url = h.url_for(
                        u'{}_resource.new'.format(package_type),
                        id=pkg_dict[u'name']
                    )
                    return h.redirect_to(url)
                # Make sure we don't index this dataset
                if request.form[u'save'] not in [
                    u'go-resource', u'go-metadata'
                ]:
                    data_dict[u'state'] = u'draft'
                # allow the state to be changed
                context[u'allow_state_change'] = True

            data_dict[u'type'] = package_type
            context[u'message'] = data_dict.get(u'log_message', u'')
            pkg_dict = get_action(u'package_create')(context, data_dict)

            if ckan_phase:
                # redirect to add dataset resources
                url = h.url_for(
                    u'{}_resource.new'.format(package_type),
                    id=pkg_dict[u'name']
                )
                return h.redirect_to(url)

            return _form_save_redirect(
                pkg_dict[u'name'], u'new', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to read package'))
        except NotFound as e:
            return base.abort(404, _(u'Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = text_type(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = text_type(str(e))
            return base.abort(
                500,
                _(u'Unable to add package to search index.') + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if is_an_update:
                # we need to get the state of the dataset to show the stage we
                # are on.
                pkg_dict = get_action(u'package_show')(context, data_dict)
                data_dict[u'state'] = pkg_dict[u'state']
                return EditView().get(
                    package_type,
                    data_dict[u'id'],
                    data_dict,
                    errors,
                    error_summary
                )
            data_dict[u'state'] = u'none'
            return self.get(package_type, data_dict, errors, error_summary)

    def get(self, package_type, data=None, errors=None, error_summary=None):
        context = self._prepare(data)
        if data and u'type' in data:
            package_type = data[u'type']

        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.args, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )
        resources_json = h.json.dumps(data.get(u'resources', []))
        # convert tags if not supplied in data
        if data and not data.get(u'tag_string'):
            data[u'tag_string'] = u', '.join(
                h.dict_list_reduce(data.get(u'tags', {}), u'name')
            )

        errors = errors or {}
        error_summary = error_summary or {}
        # in the phased add dataset we need to know that
        # we have already completed stage 1
        stage = [u'active']
        if data.get(u'state', u'').startswith(u'draft'):
            stage = [u'active', u'complete']

        # if we are creating from a group then this allows the group to be
        # set automatically
        data[
            u'group_id'
        ] = request.args.get(u'group') or request.args.get(u'groups__0__id')

        form_snippet = _get_pkg_template(
            u'package_form', package_type=package_type
        )
        form_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'new',
            u'stage': stage,
            u'dataset_type': package_type,
            u'form_style': u'new'
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(context, {}, package_type=package_type)

        new_template = _get_pkg_template(u'new_template', package_type)
        return base.render(
            new_template,
            extra_vars={
                u'form_vars': form_vars,
                u'form_snippet': form_snippet,
                u'dataset_type': package_type,
                u'resources_json': resources_json,
                u'form_snippet': form_snippet,
                u'errors_json': errors_json
            }
        )


class EditView(MethodView):
    def _prepare(self, id, data=None):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj,
            u'save': u'save' in request.form
        }
        return context

    def post(self, package_type, id):
        context = self._prepare(id)
        package_type = _get_package_type(id) or package_type
        log.debug(u'Package save request name: %s POST: %r', id, request.form)
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        try:
            if u'_ckan_phase' in data_dict:
                # we allow partial updates to not destroy existing resources
                context[u'allow_partial_update'] = True
                if u'tag_string' in data_dict:
                    data_dict[u'tags'] = _tag_string_to_list(
                        data_dict[u'tag_string']
                    )
                del data_dict[u'_ckan_phase']
                del data_dict[u'save']
            context[u'message'] = data_dict.get(u'log_message', u'')
            data_dict['id'] = id
            pkg_dict = get_action(u'package_update')(context, data_dict)

            return _form_save_redirect(
                pkg_dict[u'name'], u'edit', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to read package %s') % id)
        except NotFound as e:
            return base.abort(404, _(u'Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = text_type(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = text_type(str(e))
            return base.abort(
                500,
                _(u'Unable to update search index.') + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(package_type, id, data_dict, errors, error_summary)

    def get(
        self, package_type, id, data=None, errors=None, error_summary=None
    ):
        context = self._prepare(id, data)
        package_type = _get_package_type(id) or package_type
        try:
            pkg_dict = get_action(u'package_show')(
                dict(context, for_view=True), {
                    u'id': id
                }
            )
            context[u'for_edit'] = True
            old_data = get_action(u'package_show')(context, {u'id': id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            if data:
                old_data.update(data)
            data = old_data
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Dataset not found'))
        # are we doing a multiphase add?
        if data.get(u'state', u'').startswith(u'draft'):
            g.form_action = h.url_for(u'{}.new'.format(package_type))
            g.form_style = u'new'

            return CreateView().get(
                package_type,
                data=data,
                errors=errors,
                error_summary=error_summary
            )

        pkg = context.get(u"package")
        resources_json = h.json.dumps(data.get(u'resources', []))

        try:
            check_access(u'package_update', context)
        except NotAuthorized:
            return base.abort(
                403,
                _(u'User %r not authorized to edit %s') % (g.user, id)
            )
        # convert tags if not supplied in data
        if data and not data.get(u'tag_string'):
            data[u'tag_string'] = u', '.join(
                h.dict_list_reduce(pkg_dict.get(u'tags', {}), u'name')
            )
        errors = errors or {}
        form_snippet = _get_pkg_template(
            u'package_form', package_type=package_type
        )
        form_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'edit',
            u'dataset_type': package_type,
            u'form_style': u'edit'
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.pkg = pkg
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(
            context, {u'id': id}, package_type=package_type
        )

        # we have already completed stage 1
        form_vars[u'stage'] = [u'active']
        if data.get(u'state', u'').startswith(u'draft'):
            form_vars[u'stage'] = [u'active', u'complete']

        edit_template = _get_pkg_template(u'edit_template', package_type)
        return base.render(
            edit_template,
            extra_vars={
                u'form_vars': form_vars,
                u'form_snippet': form_snippet,
                u'dataset_type': package_type,
                u'pkg_dict': pkg_dict,
                u'pkg': pkg,
                u'resources_json': resources_json,
                u'form_snippet': form_snippet,
                u'errors_json': errors_json
            }
        )


class DeleteView(MethodView):
    def _prepare(self):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        return context

    def post(self, package_type, id):
        if u'cancel' in request.form:
            return h.redirect_to(u'{}.edit'.format(package_type), id=id)
        context = self._prepare()
        try:
            get_action(u'package_delete')(context, {u'id': id})
        except NotFound:
            return base.abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete package %s') % u''
            )

        h.flash_notice(_(u'Dataset has been deleted.'))
        return h.redirect_to(package_type + u'.search')

    def get(self, package_type, id):
        context = self._prepare()
        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
        except NotFound:
            return base.abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete package %s') % u''
            )

        dataset_type = pkg_dict[u'type'] or package_type

        # TODO: remove
        g.pkg_dict = pkg_dict

        return base.render(
            u'package/confirm_delete.html', {
                u'pkg_dict': pkg_dict,
                u'dataset_type': dataset_type
            }
        )


def follow(package_type, id):
    """Start following this dataset.
    """
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id}
    try:
        get_action(u'follow_dataset')(context, data_dict)
        package_dict = get_action(u'package_show')(context, data_dict)
        id = package_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except NotAuthorized as e:
        h.flash_error(e.message)
    else:
        h.flash_success(
            _(u"You are now following {0}").format(package_dict[u'title'])
        )

    return h.redirect_to(u'{}.read'.format(package_type), id=id)


def unfollow(package_type, id):
    """Stop following this dataset.
    """
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id}
    try:
        get_action(u'unfollow_dataset')(context, data_dict)
        package_dict = get_action(u'package_show')(context, data_dict)
        id = package_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except (NotFound, NotAuthorized) as e:
        error_message = e.message
        h.flash_error(error_message)
    else:
        h.flash_success(
            _(u"You are no longer following {0}").format(
                package_dict[u'title']
            )
        )

    return h.redirect_to(u'{}.read'.format(package_type), id=id)


def followers(package_type, id=None):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }

    data_dict = {u'id': id}
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
        followers = get_action(u'dataset_follower_list')(
            context, {
                u'id': pkg_dict[u'id']
            }
        )

        dataset_type = pkg.type or package_type
    except NotFound:
        return base.abort(404, _(u'Dataset not found'))
    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized to read package %s') % id)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg
    g.followers = followers

    return base.render(
        u'package/followers.html', {
            u'dataset_type': dataset_type,
            u'pkg_dict': pkg_dict,
            u'pkg': pkg,
            u'followers': followers
        }
    )


class GroupView(MethodView):
    def _prepare(self, id):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'for_view': True,
            u'auth_user_obj': g.userobj,
            u'use_cache': False
        }

        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Dataset not found'))
        return context, pkg_dict

    def post(self, package_type, id):
        context, pkg_dict = self._prepare(id)
        new_group = request.form.get(u'group_added')
        if new_group:
            data_dict = {
                u"id": new_group,
                u"object": id,
                u"object_type": u'package',
                u"capacity": u'public'
            }
            try:
                get_action(u'member_create')(context, data_dict)
            except NotFound:
                return base.abort(404, _(u'Group not found'))

        removed_group = None
        for param in request.form:
            if param.startswith(u'group_remove'):
                removed_group = param.split(u'.')[-1]
                break
        if removed_group:
            data_dict = {
                u"id": removed_group,
                u"object": id,
                u"object_type": u'package'
            }

            try:
                get_action(u'member_delete')(context, data_dict)
            except NotFound:
                return base.abort(404, _(u'Group not found'))
        return h.redirect_to(u'{}.groups'.format(package_type), id=id)

    def get(self, package_type, id):
        context, pkg_dict = self._prepare(id)
        dataset_type = pkg_dict[u'type'] or package_type
        context[u'is_member'] = True
        users_groups = get_action(u'group_list_authz')(context, {u'id': id})

        pkg_group_ids = set(
            group[u'id'] for group in pkg_dict.get(u'groups', [])
        )

        user_group_ids = set(group[u'id'] for group in users_groups)

        group_dropdown = [[group[u'id'], group[u'display_name']]
                          for group in users_groups
                          if group[u'id'] not in pkg_group_ids]

        for group in pkg_dict.get(u'groups', []):
            group[u'user_member'] = (group[u'id'] in user_group_ids)

        # TODO: remove
        g.pkg_dict = pkg_dict
        g.group_dropdown = group_dropdown

        return base.render(
            u'package/group_list.html', {
                u'dataset_type': dataset_type,
                u'pkg_dict': pkg_dict,
                u'group_dropdown': group_dropdown
            }
        )


def activity(package_type, id):
    """Render this package's public activity stream page.
    """
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id}
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
        package_activity_stream = get_action(
            u'package_activity_list')(
            context, {u'id': pkg_dict[u'id']})
        dataset_type = pkg_dict[u'type'] or u'dataset'
    except NotFound:
        return base.abort(404, _(u'Dataset not found'))
    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized to read dataset %s') % id)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg

    return base.render(
        u'package/activity.html', {
            u'dataset_type': dataset_type,
            u'pkg_dict': pkg_dict,
            u'pkg': pkg,
            u'activity_stream': package_activity_stream,
            u'id': id,  # i.e. package's current name
        }
    )


def changes(id, package_type=None):
    '''
    Shows the changes to a dataset in one particular activity stream item.
    '''
    activity_id = id
    context = {
        u'model': model, u'session': model.Session,
        u'user': g.user, u'auth_user_obj': g.userobj
    }
    try:
        activity_diff = get_action(u'activity_diff')(
            context, {u'id': activity_id, u'object_type': u'package',
                      u'diff_type': u'html'})
    except NotFound as e:
        log.info(u'Activity not found: {} - {}'.format(str(e), activity_id))
        return base.abort(404, _(u'Activity not found'))
    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized to view activity data'))

    # 'pkg_dict' needs to go to the templates for page title & breadcrumbs.
    # Use the current version of the package, in case the name/title have
    # changed, and we need a link to it which works
    pkg_id = activity_diff[u'activities'][1][u'data'][u'package'][u'id']
    current_pkg_dict = get_action(u'package_show')(context, {u'id': pkg_id})
    pkg_activity_list = get_action(u'package_activity_list')(
        context, {
            u'id': pkg_id,
            u'limit': 100
        }
    )

    return base.render(
        u'package/changes.html', {
            u'activity_diffs': [activity_diff],
            u'pkg_dict': current_pkg_dict,
            u'pkg_activity_list': pkg_activity_list,
            u'dataset_type': current_pkg_dict[u'type'],
        }
    )


def changes_multiple(package_type=None):
    '''
    Called when a user specifies a range of versions they want to look at
    changes between. Verifies that the range is valid and finds the set of
    activity diffs for the changes in the given version range, then
    re-renders changes.html with the list.
    '''

    new_id = h.get_request_param(u'new_id')
    old_id = h.get_request_param(u'old_id')

    context = {
        u'model': model, u'session': model.Session,
        u'user': g.user, u'auth_user_obj': g.userobj
    }

    # check to ensure that the old activity is actually older than
    # the new activity
    old_activity = get_action(u'activity_show')(context, {
        u'id': old_id,
        u'include_data': False})
    new_activity = get_action(u'activity_show')(context, {
        u'id': new_id,
        u'include_data': False})

    old_timestamp = old_activity[u'timestamp']
    new_timestamp = new_activity[u'timestamp']

    t1 = datetime.strptime(old_timestamp, u'%Y-%m-%dT%H:%M:%S.%f')
    t2 = datetime.strptime(new_timestamp, u'%Y-%m-%dT%H:%M:%S.%f')

    time_diff = t2 - t1
    # if the time difference is negative, just return the change that put us
    # at the more recent ID we were just looking at
    # TODO: do something better here - go back to the previous page,
    # display a warning that the user can't look at a sequence where
    # the newest item is older than the oldest one, etc
    if time_diff.total_seconds() < 0:
        return changes(h.get_request_param(u'current_new_id'))

    done = False
    current_id = new_id
    diff_list = []

    while not done:
        try:
            activity_diff = get_action(u'activity_diff')(
                context, {
                    u'id': current_id,
                    u'object_type': u'package',
                    u'diff_type': u'html'})
        except NotFound as e:
            log.info(
                u'Activity not found: {} - {}'.format(str(e), current_id)
            )
            return base.abort(404, _(u'Activity not found'))
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to view activity data'))

        diff_list.append(activity_diff)

        if activity_diff['activities'][0]['id'] == old_id:
            done = True
        else:
            current_id = activity_diff['activities'][0]['id']

    pkg_id = diff_list[0][u'activities'][1][u'data'][u'package'][u'id']
    current_pkg_dict = get_action(u'package_show')(context, {u'id': pkg_id})
    pkg_activity_list = get_action(u'package_activity_list')(context, {
        u'id': pkg_id,
        u'limit': 100})

    return base.render(
        u'package/changes.html', {
            u'activity_diffs': diff_list,
            u'pkg_dict': current_pkg_dict,
            u'pkg_activity_list': pkg_activity_list,
            u'dataset_type': current_pkg_dict[u'type'],
        }
    )


def collaborators_read(package_type, id):
    context = {u'model': model, u'user': g.user}
    data_dict = {u'id': id}

    try:
        check_access(u'package_collaborator_list', context, data_dict)
        # needed to ckan_extend package/edit_base.html
        pkg_dict = get_action(u'package_show')(context, data_dict)
    except NotAuthorized:
        message = _(u'Unauthorized to read collaborators {}').format(id)
        return base.abort(401, message)
    except NotFound:
        return base.abort(404, _(u'Dataset not found'))

    return base.render(u'package/collaborators/collaborators.html', {
        u'pkg_dict': pkg_dict})


def collaborator_delete(package_type, id, user_id):
    context = {u'model': model, u'user': g.user}

    try:
        get_action(u'package_collaborator_delete')(context, {
            u'id': id,
            u'user_id': user_id
        })
    except NotAuthorized:
        message = _(u'Unauthorized to delete collaborators {}').format(id)
        return base.abort(401, _(message))
    except NotFound as e:
        return base.abort(404, _(e.message))

    h.flash_success(_(u'User removed from collaborators'))

    return h.redirect_to(u'dataset.collaborators_read', id=id)


class CollaboratorEditView(MethodView):

    def post(self, package_type, id):
        context = {u'model': model, u'user': g.user}

        try:
            form_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(request.form))))

            user = get_action(u'user_show')(
                context, {u'id': form_dict[u'username']}
            )

            data_dict = {
                u'id': id,
                u'user_id': user[u'id'],
                u'capacity': form_dict[u'capacity']
            }

            get_action(u'package_collaborator_create')(
                context, data_dict)

        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        except NotAuthorized:
            message = _(u'Unauthorized to edit collaborators {}').format(id)
            return base.abort(401, _(message))
        except NotFound:
            return base.abort(404, _(u'Resource not found'))
        except ValidationError as e:
            h.flash_error(e.error_summary)
        else:
            h.flash_success(_(u'User added to collaborators'))

        return h.redirect_to(u'dataset.collaborators_read', id=id)

    def get(self, package_type, id):
        context = {u'model': model, u'user': g.user}
        data_dict = {u'id': id}

        try:
            check_access(u'package_collaborator_list', context, data_dict)
            # needed to ckan_extend package/edit_base.html
            pkg_dict = get_action(u'package_show')(context, data_dict)
        except NotAuthorized:
            message = u'Unauthorized to read collaborators {}'.format(id)
            return base.abort(401, _(message))
        except NotFound:
            return base.abort(404, _(u'Resource not found'))

        user = request.params.get(u'user_id')
        user_capacity = u'member'

        if user:
            collaborators = get_action(u'package_collaborator_list')(
                context, data_dict)
            for c in collaborators:
                if c[u'user_id'] == user:
                    user_capacity = c[u'capacity']
            user = get_action(u'user_show')(context, {u'id': user})

        capacities = []
        if authz.check_config_permission(u'allow_admin_collaborators'):
            capacities.append({u'name': u'admin', u'value': u'admin'})
        capacities.extend([
            {u'name': u'editor', u'value': u'editor'},
            {u'name': u'member', u'value': u'member'}
        ])

        extra_vars = {
            u'capacities': capacities,
            u'user_capacity': user_capacity,
            u'user': user,
            u'pkg_dict': pkg_dict,
        }

        return base.render(
            u'package/collaborators/collaborator_new.html', extra_vars)


# deprecated
def history(package_type, id):
    return h.redirect_to(u'{}.activity'.format(package_type), id=id)


def register_dataset_plugin_rules(blueprint):
    blueprint.add_url_rule(u'/', view_func=search, strict_slashes=False)
    blueprint.add_url_rule(u'/new', view_func=CreateView.as_view(str(u'new')))
    blueprint.add_url_rule(u'/<id>', view_func=read)
    blueprint.add_url_rule(u'/resources/<id>', view_func=resources)
    blueprint.add_url_rule(
        u'/edit/<id>', view_func=EditView.as_view(str(u'edit'))
    )
    blueprint.add_url_rule(
        u'/delete/<id>', view_func=DeleteView.as_view(str(u'delete'))
    )
    blueprint.add_url_rule(
        u'/follow/<id>', view_func=follow, methods=(u'POST', )
    )
    blueprint.add_url_rule(
        u'/unfollow/<id>', view_func=unfollow, methods=(u'POST', )
    )
    blueprint.add_url_rule(u'/followers/<id>', view_func=followers)
    blueprint.add_url_rule(
        u'/groups/<id>', view_func=GroupView.as_view(str(u'groups'))
    )
    blueprint.add_url_rule(u'/activity/<id>', view_func=activity)
    blueprint.add_url_rule(u'/changes/<id>', view_func=changes)
    blueprint.add_url_rule(u'/<id>/history', view_func=history)

    blueprint.add_url_rule(u'/changes_multiple', view_func=changes_multiple)

    # Duplicate resource create and edit for backward compatibility. Note,
    # we cannot use resource.CreateView directly here, because of
    # circular imports
    blueprint.add_url_rule(
        u'/new_resource/<id>',
        view_func=LazyView(
            u'ckan.views.resource.CreateView', str(u'new_resource')
        )
    )

    blueprint.add_url_rule(
        u'/<id>/resource_edit/<resource_id>',
        view_func=LazyView(
            u'ckan.views.resource.EditView', str(u'edit_resource')
        )

    )

    if authz.check_config_permission(u'allow_dataset_collaborators'):
        blueprint.add_url_rule(
            rule=u'/collaborators/<id>',
            view_func=collaborators_read,
            methods=['GET', ]
        )

        blueprint.add_url_rule(
            rule=u'/collaborators/<id>/new',
            view_func=CollaboratorEditView.as_view(str(u'new_collaborator')),
            methods=[u'GET', u'POST', ]
        )

        blueprint.add_url_rule(
            rule=u'/collaborators/<id>/delete/<user_id>',
            view_func=collaborator_delete, methods=['POST', ]
        )


register_dataset_plugin_rules(dataset)
