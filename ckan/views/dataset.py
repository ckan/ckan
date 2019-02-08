# encoding: utf-8
import logging
from collections import OrderedDict
from functools import partial
from urllib import urlencode
import datetime

from flask import Blueprint, make_response
from flask.views import MethodView
from paste.deploy.converters import asbool
from six import string_types, text_type

import ckan.lib.i18n as i18n
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
from ckan.common import _, config, g, request
from ckan.controllers.home import CACHE_PARAMETERS
from ckan.lib.plugins import lookup_package_plugin
from ckan.lib.render import TemplateNotFound
from ckan.lib.search import SearchError, SearchQueryError, SearchIndexError
from ckan.views import LazyView
from ckan.views.api import CONTENT_TYPES

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
    return getattr(pkg_plugin, template_type)()


def _encode_params(params):
    return [(k, v.encode(u'utf-8') if isinstance(v, string_types) else str(v))
            for k, v in params]


def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)


def search_url(params, package_type=None):
    if not package_type or package_type == u'dataset':
        url = h.url_for(u'dataset.search')
    else:
        url = h.url_for(u'{0}_search'.format(package_type))
    return url_with_params(url, params)


def drill_down_url(alternative_url=None, **by):
    return h.add_url_param(
        alternative_url=alternative_url,
        controller=u'dataset',
        action=u'search',
        new_params=by
    )


def remove_field(package_type, key, value=None, replace=None):
    return h.remove_url_param(
        key,
        value=value,
        replace=replace,
        controller=u'dataset',
        action=u'search',
        alternative_url=package_type
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
        if package_type is None or package_type == u'dataset':
            url = h.url_for(u'dataset.read', id=pkg_name)
        else:
            url = h.url_for(u'{0}_read'.format(package_type), id=pkg_name)
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

    try:
        # fields_grouped will contain a dict of params containing
        # a list of values eg {u'tags':[u'tag1', u'tag2']}

        extra_vars[u'fields'] = fields = []
        extra_vars[u'fields_grouped'] = fields_grouped = {}
        search_extras = {}
        fq = u''
        for (param, value) in request.args.items():
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
                    search_extras[param] = value

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

        default_facet_titles = {
            u'organization': _(u'Organizations'),
            u'groups': _(u'Groups'),
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
            u'facet.field': facets.keys(),
            u'rows': limit,
            u'start': (page - 1) * limit,
            u'sort': sort_by,
            u'extras': search_extras,
            u'include_private': asbool(
                config.get(u'ckan.search.default_include_private', True)
            ),
        }

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
    for key, value in extra_vars.iteritems():
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

    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Dataset not found'))

    g.pkg_dict = pkg_dict
    g.pkg = pkg

    # if the user specified a package id, redirect to the package name
    if data_dict['id'] == pkg_dict['id'] and \
            data_dict['id'] != pkg_dict['name']:
        return h.redirect_to(u'dataset.read',
                             id=pkg_dict['name'])

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
                u'pkg': pkg
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
                    url = h.url_for(u'resource.new', id=pkg_dict[u'name'])
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
                url = h.url_for(u'resource.new', id=pkg_dict[u'name'])
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
                    data_dict[u'id'], data_dict, errors, error_summary
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
            g.form_action = h.url_for(u'dataset.new')
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
            return h.redirect_to(u'dataset.edit', id=id)
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

    return h.redirect_to(u'dataset.read', id=id)


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

    return h.redirect_to(u'dataset.read', id=id)


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
        return h.redirect_to(u'dataset.groups', id=id)

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


def history(package_type, id):
    if u'diff' in request.args or u'selected1' in request.args:
        try:
            params = {
                u'id': request.args.getone(u'pkg_name'),
                u'diff': request.args.getone(u'selected1'),
                u'oldid': request.args.getone(u'selected2'),
            }
        except KeyError:
            if u'pkg_name' in dict(request.args):
                id = request.args.getone(u'pkg_name')
            g.error = \
                _(u'Select two revisions before doing the comparison.')
        else:
            params[u'diff_entity'] = u'package'
            return h.redirect_to(
                controller=u'revision', action=u'diff', **params
            )

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    data_dict = {u'id': id}
    try:
        g.pkg_dict = get_action(u'package_show')(context, data_dict)
        g.pkg_revisions = get_action(u'package_revision_list')(
            context, data_dict
        )
        # TODO: remove
        # Still necessary for the authz check in group/layout.html
        g.pkg = context[u'package']

    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized to read package %s') % u'')
    except NotFound:
        return base.abort(404, _(u'Dataset not found'))

    format = request.args.get(u'format', u'')
    if format == u'atom':
        # Generate and return Atom 1.0 document.
        from webhelpers.feedgenerator import Atom1Feed
        feed = Atom1Feed(
            title=_(u'CKAN Dataset Revision History'),
            link=h.url_for(
                controller=u'revision', action=u'read', id=g.pkg_dict[u'name']
            ),
            description=_(u'Recent changes to CKAN Dataset: ') +
            (g.pkg_dict[u'title'] or u''),
            language=text_type(i18n.get_lang()),
        )
        for revision_dict in g.pkg_revisions:
            revision_date = h.date_str_to_datetime(revision_dict[u'timestamp'])
            try:
                dayHorizon = int(request.args.get(u'days'))
            except Exception:
                dayHorizon = 30
            dayAge = (datetime.datetime.now() - revision_date).days
            if dayAge >= dayHorizon:
                break
            if revision_dict[u'message']:
                item_title = u'%s' % revision_dict[u'message'].\
                    split(u'\n')[0]
            else:
                item_title = u'%s' % revision_dict[u'id']
            item_link = h.url_for(
                controller=u'revision',
                action=u'read',
                id=revision_dict[u'id']
            )
            item_description = _(u'Log message: ')
            item_description += u'%s' % (revision_dict[u'message'] or u'')
            item_author_name = revision_dict[u'author']
            item_pubdate = revision_date
            feed.add_item(
                title=item_title,
                link=item_link,
                description=item_description,
                author_name=item_author_name,
                pubdate=item_pubdate,
            )
        response = make_response(feed.writeString(u'utf-8'))
        response.headers[u'Content-Type'] = u'application/atom+xml'
        return response

    package_type = g.pkg_dict[u'type'] or u'dataset'

    return base.render(
        _get_pkg_template(
            u'history_template', g.pkg_dict.get(u'type', package_type)
        ),
        extra_vars={u'dataset_type': package_type}
    )


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
    blueprint.add_url_rule(u'/<id>/history', view_func=history)

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


register_dataset_plugin_rules(dataset)
