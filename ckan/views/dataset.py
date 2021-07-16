# encoding: utf-8
import logging
import inspect
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
    'dataset',
    __name__,
    url_prefix='/dataset',
    url_defaults={'package_type': 'dataset'}
)


def _setup_template_variables(context, data_dict, package_type=None):
    return lookup_package_plugin(package_type).setup_template_variables(
        context, data_dict
    )


def _get_pkg_template(template_type, package_type=None):
    pkg_plugin = lookup_package_plugin(package_type)
    method = getattr(pkg_plugin, template_type)
    signature = inspect.signature(method)
    if len(signature.parameters):
        return method(package_type)
    else:
        return method()


def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, string_types) else str(v))
            for k, v in params]


def url_with_params(url, params):
    params = _encode_params(params)
    return url + '?' + urlencode(params)


def search_url(params, package_type=None):
    if not package_type:
        package_type = 'dataset'
    url = h.url_for('{0}.search'.format(package_type))
    return url_with_params(url, params)


def drill_down_url(alternative_url=None, **by):
    return h.add_url_param(
        alternative_url=alternative_url,
        controller='dataset',
        action='search',
        new_params=by
    )


def remove_field(package_type, key, value=None, replace=None):
    if not package_type:
        package_type = 'dataset'
    url = h.url_for('{0}.search'.format(package_type))
    return h.remove_url_param(
        key,
        value=value,
        replace=replace,
        alternative_url=url
    )


def _sort_by(params_nosort, package_type, fields):
    """Sort by the given list of fields.

    Each entry in the list is a 2-tuple: (fieldname, sort_order)
    eg - [('metadata_modified', 'desc'), ('name', 'asc')]
    If fields is empty, then the default ordering is used.
    """
    params = params_nosort[:]

    if fields:
        sort_string = ', '.join('%s %s' % f for f in fields)
        params.append(('sort', sort_string))
    return search_url(params, package_type)


def _pager_url(params_nopage, package_type, q=None, page=None):
    params = list(params_nopage)
    params.append(('page', page))
    return search_url(params, package_type)


def _tag_string_to_list(tag_string):
    """This is used to change tags from a sting to a list of dicts.
    """
    out = []
    for tag in tag_string.split(','):
        tag = tag.strip()
        if tag:
            out.append({'name': tag, 'state': 'active'})
    return out


def _form_save_redirect(pkg_name, action, package_type=None):
    """This redirects the user to the CKAN package/read page,
    unless there is request parameter giving an alternate location,
    perhaps an external website.
    @param pkg_name - Name of the package just edited
    @param action - What the action of the edit was
    """
    assert action in ('new', 'edit')
    url = request.args.get('return_to') or config.get(
        'package_%s_return_url' % action
    )
    if url:
        url = url.replace('<NAME>', pkg_name)
    else:
        if not package_type:
            package_type = 'dataset'
        url = h.url_for('{0}.read'.format(package_type), id=pkg_name)
    return h.redirect_to(url)


def _get_package_type(id):
    """
    Given the id of a package this method will return the type of the
    package, or 'dataset' if no type is currently set
    """
    pkg = model.Package.get(id)
    if pkg:
        return pkg.type or 'dataset'
    return None


def _get_search_details():
    fq = ''

    # fields_grouped will contain a dict of params containing
    # a list of values eg {'tags':['tag1', 'tag2']}

    fields = []
    fields_grouped = {}
    search_extras = MultiDict()

    for (param, value) in request.args.items(multi=True):
        if param not in ['q', 'page', 'sort'] \
                and len(value) and not param.startswith('_'):
            if not param.startswith('ext_'):
                fields.append((param, value))
                fq += ' %s:"%s"' % (param, value)
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
        'fields': fields,
        'fields_grouped': fields_grouped,
        'fq': fq,
        'search_extras': search_extras,
    }


def search(package_type):
    extra_vars = {}

    try:
        context = {
            'model': model,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        check_access('site_read', context)
    except NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    # unicode format (decoded from utf8)
    extra_vars['q'] = q = request.args.get('q', '')

    extra_vars['query_error'] = False
    page = h.get_page_number(request.args)

    limit = int(config.get('ckan.datasets_per_page', 20))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.args.items(multi=True)
                     if k != 'page']

    extra_vars['drill_down_url'] = drill_down_url
    extra_vars['remove_field'] = partial(remove_field, package_type)

    sort_by = request.args.get('sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

    extra_vars['sort_by'] = partial(_sort_by, params_nosort, package_type)

    if not sort_by:
        sort_by_fields = []
    else:
        sort_by_fields = [field.split()[0] for field in sort_by.split(',')]
    extra_vars['sort_by_fields'] = sort_by_fields

    pager_url = partial(_pager_url, params_nopage, package_type)

    search_url_params = urlencode(_encode_params(params_nopage))
    extra_vars['search_url_params'] = search_url_params

    details = _get_search_details()
    extra_vars['fields'] = details['fields']
    extra_vars['fields_grouped'] = details['fields_grouped']
    fq = details['fq']
    search_extras = details['search_extras']

    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True,
        'auth_user_obj': g.userobj
    }

    # Unless changed via config options, don't show other dataset
    # types any search page. Potential alternatives are do show them
    # on the default search page (dataset) or on one other search page
    search_all_type = config.get('ckan.search.show_all_types', 'dataset')
    search_all = False

    try:
        # If the "type" is set to True or False, convert to bool
        # and we know that no type was specified, so use traditional
        # behaviour of applying this only to dataset type
        search_all = asbool(search_all_type)
        search_all_type = 'dataset'
    # Otherwise we treat as a string representing a type
    except ValueError:
        search_all = True

    if not search_all or package_type != search_all_type:
        # Only show datasets of this particular type
        fq += ' +dataset_type:{type}'.format(type=package_type)

    facets = OrderedDict()

    org_label = h.humanize_entity_type(
        'organization',
        h.default_group_type('organization'),
        'facet label') or _('Organizations')

    group_label = h.humanize_entity_type(
        'group',
        h.default_group_type('group'),
        'facet label') or _('Groups')

    default_facet_titles = {
        'organization': org_label,
        'groups': group_label,
        'tags': _('Tags'),
        'res_format': _('Formats'),
        'license_id': _('Licenses'),
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, package_type)

    extra_vars['facet_titles'] = facets
    data_dict = {
        'q': q,
        'fq': fq.strip(),
        'facet.field': list(facets.keys()),
        'rows': limit,
        'start': (page - 1) * limit,
        'sort': sort_by,
        'extras': search_extras,
        'include_private': asbool(
            config.get('ckan.search.default_include_private', True)
        ),
    }
    try:
        query = get_action('package_search')(context, data_dict)

        extra_vars['sort_by_selected'] = query['sort']

        extra_vars['page'] = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit
        )
        extra_vars['search_facets'] = query['search_facets']
        extra_vars['page'].items = query['results']
    except SearchQueryError as se:
        # User's search parameters are invalid, in such a way that is not
        # achievable with the web interface, so return a proper error to
        # discourage spiders which are the main cause of this.
        log.info('Dataset search query rejected: %r', se.args)
        base.abort(
            400,
            _('Invalid search query: {error_message}')
            .format(error_message=str(se))
        )
    except SearchError as se:
        # May be bad input from the user, but may also be more serious like
        # bad code causing a SOLR syntax error, or a problem connecting to
        # SOLR
        log.error('Dataset search error: %r', se.args)
        extra_vars['query_error'] = True
        extra_vars['search_facets'] = {}
        extra_vars['page'] = h.Page(collection=[])

    # FIXME: try to avoid using global variables
    g.search_facets_limits = {}
    for facet in extra_vars['search_facets'].keys():
        try:
            limit = int(
                request.args.get(
                    '_%s_limit' % facet,
                    int(config.get('search.facets.default', 10))
                )
            )
        except ValueError:
            base.abort(
                400,
                _('Parameter "{parameter_name}" is not '
                  'an integer').format(parameter_name='_%s_limit' % facet)
            )

        g.search_facets_limits[facet] = limit

    _setup_template_variables(context, {}, package_type=package_type)

    extra_vars['dataset_type'] = package_type

    # TODO: remove
    for key, value in six.iteritems(extra_vars):
        setattr(g, key, value)

    return base.render(
        _get_pkg_template('search_template', package_type), extra_vars
    )


def resources(package_type, id):
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id, 'include_tracking': True}

    try:
        check_access('package_update', context, data_dict)
    except NotFound:
        return base.abort(404, _('Dataset not found'))
    except NotAuthorized:
        return base.abort(
            403,
            _('User %r not authorized to edit %s') % (g.user, id)
        )
    # check if package exists
    try:
        pkg_dict = get_action('package_show')(context, data_dict)
        pkg = context['package']
    except (NotFound, NotAuthorized):
        return base.abort(404, _('Dataset not found'))

    package_type = pkg_dict['type'] or 'dataset'
    _setup_template_variables(context, {'id': id}, package_type=package_type)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg

    return base.render(
        'package/resources.html', {
            'dataset_type': package_type,
            'pkg_dict': pkg_dict,
            'pkg': pkg
        }
    )


def read(package_type, id):
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id, 'include_tracking': True}
    activity_id = request.params.get('activity_id')

    # check if package exists
    try:
        pkg_dict = get_action('package_show')(context, data_dict)
        pkg = context['package']
    except (NotFound, NotAuthorized):
        return base.abort(404, _('Dataset not found'))

    g.pkg_dict = pkg_dict
    g.pkg = pkg
    # NB templates should not use g.pkg, because it takes no account of
    # activity_id

    if activity_id:
        # view an 'old' version of the package, as recorded in the
        # activity stream
        try:
            activity = get_action('activity_show')(
                context, {'id': activity_id, 'include_data': True})
        except NotFound:
            base.abort(404, _('Activity not found'))
        except NotAuthorized:
            base.abort(403, _('Unauthorized to view activity data'))
        current_pkg = pkg_dict
        try:
            pkg_dict = activity['data']['package']
        except KeyError:
            base.abort(404, _('Dataset not found'))
        if 'id' not in pkg_dict or 'resources' not in pkg_dict:
            log.info('Attempt to view unmigrated or badly migrated dataset '
                     '{} {}'.format(id, activity_id))
            base.abort(404, _('The detail of this dataset activity is not '
                              'available'))
        if pkg_dict['id'] != current_pkg['id']:
            log.info('Mismatch between pkg id in activity and URL {} {}'
                     .format(pkg_dict['id'], current_pkg['id']))
            # the activity is not for the package in the URL - don't allow
            # misleading URLs as could be malicious
            base.abort(404, _('Activity not found'))
        # The name is used lots in the template for links, so fix it to be
        # the current one. It's not displayed to the user anyway.
        pkg_dict['name'] = current_pkg['name']

        # Earlier versions of CKAN only stored the package table in the
        # activity, so add a placeholder for resources, or the template
        # will crash.
        pkg_dict.setdefault('resources', [])

    # if the user specified a package id, redirect to the package name
    if data_dict['id'] == pkg_dict['id'] and \
            data_dict['id'] != pkg_dict['name']:
        return h.redirect_to('{}.read'.format(package_type),
                             id=pkg_dict['name'],
                             activity_id=activity_id)

    # can the resources be previewed?
    for resource in pkg_dict['resources']:
        resource_views = get_action('resource_view_list')(
            context, {
                'id': resource['id']
            }
        )
        resource['has_views'] = len(resource_views) > 0

    package_type = pkg_dict['type'] or package_type
    _setup_template_variables(context, {'id': id}, package_type=package_type)

    template = _get_pkg_template('read_template', package_type)
    try:
        return base.render(
            template, {
                'dataset_type': package_type,
                'pkg_dict': pkg_dict,
                'pkg': pkg,  # NB deprecated - it is the current version of
                              # the dataset, so ignores activity_id
                'is_activity_archive': bool(activity_id),
            }
        )
    except TemplateNotFound as e:
        msg = _(
            "Viewing datasets of type \"{package_type}\" is "
            "not supported ({file_!r}).".format(
                package_type=package_type, file_=e.message
            )
        )
        return base.abort(404, msg)

    assert False, "We should never get here"


class CreateView(MethodView):
    def _is_save(self):
        return 'save' in request.form

    def _prepare(self, data=None):

        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj,
            'save': self._is_save()
        }
        try:
            check_access('package_create', context)
        except NotAuthorized:
            return base.abort(403, _('Unauthorized to create a package'))
        return context

    def post(self, package_type):
        # The staged add dataset used the new functionality when the dataset is
        # partially created so we need to know if we actually are updating or
        # this is a real new.
        context = self._prepare()
        is_an_update = False
        ckan_phase = request.form.get('_ckan_phase')
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _('Integrity Error'))
        try:
            if ckan_phase:
                # prevent clearing of groups etc
                context['allow_partial_update'] = True
                # sort the tags
                if 'tag_string' in data_dict:
                    data_dict['tags'] = _tag_string_to_list(
                        data_dict['tag_string']
                    )
                if data_dict.get('pkg_name'):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict['id'] = data_dict['pkg_name']
                    del data_dict['pkg_name']
                    # don't change the dataset state
                    data_dict['state'] = 'draft'
                    # this is actually an edit not a save
                    pkg_dict = get_action('package_update')(
                        context, data_dict
                    )

                    # redirect to add dataset resources
                    url = h.url_for(
                        '{}_resource.new'.format(package_type),
                        id=pkg_dict['name']
                    )
                    return h.redirect_to(url)
                # Make sure we don't index this dataset
                if request.form['save'] not in [
                    'go-resource', 'go-metadata'
                ]:
                    data_dict['state'] = 'draft'
                # allow the state to be changed
                context['allow_state_change'] = True

            data_dict['type'] = package_type
            context['message'] = data_dict.get('log_message', '')
            pkg_dict = get_action('package_create')(context, data_dict)

            if ckan_phase:
                # redirect to add dataset resources
                url = h.url_for(
                    '{}_resource.new'.format(package_type),
                    id=pkg_dict['name']
                )
                return h.redirect_to(url)

            return _form_save_redirect(
                pkg_dict['name'], 'new', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _('Unauthorized to read package'))
        except NotFound as e:
            return base.abort(404, _('Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = text_type(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = text_type(str(e))
            return base.abort(
                500,
                _('Unable to add package to search index.') + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if is_an_update:
                # we need to get the state of the dataset to show the stage we
                # are on.
                pkg_dict = get_action('package_show')(context, data_dict)
                data_dict['state'] = pkg_dict['state']
                return EditView().get(
                    package_type,
                    data_dict['id'],
                    data_dict,
                    errors,
                    error_summary
                )
            data_dict['state'] = 'none'
            return self.get(package_type, data_dict, errors, error_summary)

    def get(self, package_type, data=None, errors=None, error_summary=None):
        context = self._prepare(data)
        if data and 'type' in data:
            package_type = data['type']

        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.args, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )
        resources_json = h.json.dumps(data.get('resources', []))
        # convert tags if not supplied in data
        if data and not data.get('tag_string'):
            data['tag_string'] = ', '.join(
                h.dict_list_reduce(data.get('tags', {}), 'name')
            )

        errors = errors or {}
        error_summary = error_summary or {}
        # in the phased add dataset we need to know that
        # we have already completed stage 1
        stage = ['active']
        if data.get('state', '').startswith('draft'):
            stage = ['active', 'complete']

        # if we are creating from a group then this allows the group to be
        # set automatically
        data[
            'group_id'
        ] = request.args.get('group') or request.args.get('groups__0__id')

        form_snippet = _get_pkg_template(
            'package_form', package_type=package_type
        )
        form_vars = {
            'data': data,
            'errors': errors,
            'error_summary': error_summary,
            'action': 'new',
            'stage': stage,
            'dataset_type': package_type,
            'form_style': 'new'
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(context, {}, package_type=package_type)

        new_template = _get_pkg_template('new_template', package_type)
        return base.render(
            new_template,
            extra_vars={
                'form_vars': form_vars,
                'form_snippet': form_snippet,
                'dataset_type': package_type,
                'resources_json': resources_json,
                'form_snippet': form_snippet,
                'errors_json': errors_json
            }
        )


class EditView(MethodView):
    def _prepare(self, id, data=None):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj,
            'save': 'save' in request.form
        }
        return context

    def post(self, package_type, id):
        context = self._prepare(id)
        package_type = _get_package_type(id) or package_type
        log.debug('Package save request name: %s POST: %r', id, request.form)
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _('Integrity Error'))
        try:
            if '_ckan_phase' in data_dict:
                # we allow partial updates to not destroy existing resources
                context['allow_partial_update'] = True
                if 'tag_string' in data_dict:
                    data_dict['tags'] = _tag_string_to_list(
                        data_dict['tag_string']
                    )
                del data_dict['_ckan_phase']
                del data_dict['save']
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            pkg_dict = get_action('package_update')(context, data_dict)

            return _form_save_redirect(
                pkg_dict['name'], 'edit', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _('Unauthorized to read package %s') % id)
        except NotFound as e:
            return base.abort(404, _('Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = text_type(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = text_type(str(e))
            return base.abort(
                500,
                _('Unable to update search index.') + exc_str
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
            pkg_dict = get_action('package_show')(
                dict(context, for_view=True), {
                    'id': id
                }
            )
            context['for_edit'] = True
            old_data = get_action('package_show')(context, {'id': id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            if data:
                old_data.update(data)
            data = old_data
        except (NotFound, NotAuthorized):
            return base.abort(404, _('Dataset not found'))
        # are we doing a multiphase add?
        if data.get('state', '').startswith('draft'):
            g.form_action = h.url_for('{}.new'.format(package_type))
            g.form_style = 'new'

            return CreateView().get(
                package_type,
                data=data,
                errors=errors,
                error_summary=error_summary
            )

        pkg = context.get("package")
        resources_json = h.json.dumps(data.get('resources', []))

        try:
            check_access('package_update', context)
        except NotAuthorized:
            return base.abort(
                403,
                _('User %r not authorized to edit %s') % (g.user, id)
            )
        # convert tags if not supplied in data
        if data and not data.get('tag_string'):
            data['tag_string'] = ', '.join(
                h.dict_list_reduce(pkg_dict.get('tags', {}), 'name')
            )
        errors = errors or {}
        form_snippet = _get_pkg_template(
            'package_form', package_type=package_type
        )
        form_vars = {
            'data': data,
            'errors': errors,
            'error_summary': error_summary,
            'action': 'edit',
            'dataset_type': package_type,
            'form_style': 'edit'
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.pkg = pkg
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(
            context, {'id': id}, package_type=package_type
        )

        # we have already completed stage 1
        form_vars['stage'] = ['active']
        if data.get('state', '').startswith('draft'):
            form_vars['stage'] = ['active', 'complete']

        edit_template = _get_pkg_template('edit_template', package_type)
        return base.render(
            edit_template,
            extra_vars={
                'form_vars': form_vars,
                'form_snippet': form_snippet,
                'dataset_type': package_type,
                'pkg_dict': pkg_dict,
                'pkg': pkg,
                'resources_json': resources_json,
                'form_snippet': form_snippet,
                'errors_json': errors_json
            }
        )


class DeleteView(MethodView):
    def _prepare(self):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        return context

    def post(self, package_type, id):
        if 'cancel' in request.form:
            return h.redirect_to('{}.edit'.format(package_type), id=id)
        context = self._prepare()
        try:
            get_action('package_delete')(context, {'id': id})
        except NotFound:
            return base.abort(404, _('Dataset not found'))
        except NotAuthorized:
            return base.abort(
                403,
                _('Unauthorized to delete package %s') % ''
            )

        h.flash_notice(_('Dataset has been deleted.'))
        return h.redirect_to(package_type + '.search')

    def get(self, package_type, id):
        context = self._prepare()
        try:
            pkg_dict = get_action('package_show')(context, {'id': id})
        except NotFound:
            return base.abort(404, _('Dataset not found'))
        except NotAuthorized:
            return base.abort(
                403,
                _('Unauthorized to delete package %s') % ''
            )

        dataset_type = pkg_dict['type'] or package_type

        # TODO: remove
        g.pkg_dict = pkg_dict

        return base.render(
            'package/confirm_delete.html', {
                'pkg_dict': pkg_dict,
                'dataset_type': dataset_type
            }
        )


def follow(package_type, id):
    """Start following this dataset.
    """
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id}
    try:
        get_action('follow_dataset')(context, data_dict)
        package_dict = get_action('package_show')(context, data_dict)
        id = package_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except NotAuthorized as e:
        h.flash_error(e.message)
    else:
        h.flash_success(
            _("You are now following {0}").format(package_dict['title'])
        )

    return h.redirect_to('{}.read'.format(package_type), id=id)


def unfollow(package_type, id):
    """Stop following this dataset.
    """
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id}
    try:
        get_action('unfollow_dataset')(context, data_dict)
        package_dict = get_action('package_show')(context, data_dict)
        id = package_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except (NotFound, NotAuthorized) as e:
        error_message = e.message
        h.flash_error(error_message)
    else:
        h.flash_success(
            _("You are no longer following {0}").format(
                package_dict['title']
            )
        )

    return h.redirect_to('{}.read'.format(package_type), id=id)


def followers(package_type, id=None):
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True,
        'auth_user_obj': g.userobj
    }

    data_dict = {'id': id}
    try:
        pkg_dict = get_action('package_show')(context, data_dict)
        pkg = context['package']
        followers = get_action('dataset_follower_list')(
            context, {
                'id': pkg_dict['id']
            }
        )

        dataset_type = pkg.type or package_type
    except NotFound:
        return base.abort(404, _('Dataset not found'))
    except NotAuthorized:
        return base.abort(403, _('Unauthorized to read package %s') % id)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg
    g.followers = followers

    return base.render(
        'package/followers.html', {
            'dataset_type': dataset_type,
            'pkg_dict': pkg_dict,
            'pkg': pkg,
            'followers': followers
        }
    )


class GroupView(MethodView):
    def _prepare(self, id):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'for_view': True,
            'auth_user_obj': g.userobj,
            'use_cache': False
        }

        try:
            pkg_dict = get_action('package_show')(context, {'id': id})
        except (NotFound, NotAuthorized):
            return base.abort(404, _('Dataset not found'))
        return context, pkg_dict

    def post(self, package_type, id):
        context, pkg_dict = self._prepare(id)
        new_group = request.form.get('group_added')
        if new_group:
            data_dict = {
                "id": new_group,
                "object": id,
                "object_type": 'package',
                "capacity": 'public'
            }
            try:
                get_action('member_create')(context, data_dict)
            except NotFound:
                return base.abort(404, _('Group not found'))

        removed_group = None
        for param in request.form:
            if param.startswith('group_remove'):
                removed_group = param.split('.')[-1]
                break
        if removed_group:
            data_dict = {
                "id": removed_group,
                "object": id,
                "object_type": 'package'
            }

            try:
                get_action('member_delete')(context, data_dict)
            except NotFound:
                return base.abort(404, _('Group not found'))
        return h.redirect_to('{}.groups'.format(package_type), id=id)

    def get(self, package_type, id):
        context, pkg_dict = self._prepare(id)
        dataset_type = pkg_dict['type'] or package_type
        context['is_member'] = True
        users_groups = get_action('group_list_authz')(context, {'id': id})

        pkg_group_ids = set(
            group['id'] for group in pkg_dict.get('groups', [])
        )

        user_group_ids = set(group['id'] for group in users_groups)

        group_dropdown = [[group['id'], group['display_name']]
                          for group in users_groups
                          if group['id'] not in pkg_group_ids]

        for group in pkg_dict.get('groups', []):
            group['user_member'] = (group['id'] in user_group_ids)

        # TODO: remove
        g.pkg_dict = pkg_dict
        g.group_dropdown = group_dropdown

        return base.render(
            'package/group_list.html', {
                'dataset_type': dataset_type,
                'pkg_dict': pkg_dict,
                'group_dropdown': group_dropdown
            }
        )


def activity(package_type, id):
    """Render this package's public activity stream page.
    """
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id}
    try:
        pkg_dict = get_action('package_show')(context, data_dict)
        pkg = context['package']
        package_activity_stream = get_action(
            'package_activity_list')(
            context, {'id': pkg_dict['id']})
        dataset_type = pkg_dict['type'] or 'dataset'
    except NotFound:
        return base.abort(404, _('Dataset not found'))
    except NotAuthorized:
        return base.abort(403, _('Unauthorized to read dataset %s') % id)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg

    return base.render(
        'package/activity.html', {
            'dataset_type': dataset_type,
            'pkg_dict': pkg_dict,
            'pkg': pkg,
            'activity_stream': package_activity_stream,
            'id': id,  # i.e. package's current name
        }
    )


def changes(id, package_type=None):
    '''
    Shows the changes to a dataset in one particular activity stream item.
    '''
    activity_id = id
    context = {
        'model': model, 'session': model.Session,
        'user': g.user, 'auth_user_obj': g.userobj
    }
    try:
        activity_diff = get_action('activity_diff')(
            context, {'id': activity_id, 'object_type': 'package',
                      'diff_type': 'html'})
    except NotFound as e:
        log.info('Activity not found: {} - {}'.format(str(e), activity_id))
        return base.abort(404, _('Activity not found'))
    except NotAuthorized:
        return base.abort(403, _('Unauthorized to view activity data'))

    # 'pkg_dict' needs to go to the templates for page title & breadcrumbs.
    # Use the current version of the package, in case the name/title have
    # changed, and we need a link to it which works
    pkg_id = activity_diff['activities'][1]['data']['package']['id']
    current_pkg_dict = get_action('package_show')(context, {'id': pkg_id})
    pkg_activity_list = get_action('package_activity_list')(
        context, {
            'id': pkg_id,
            'limit': 100
        }
    )

    return base.render(
        'package/changes.html', {
            'activity_diffs': [activity_diff],
            'pkg_dict': current_pkg_dict,
            'pkg_activity_list': pkg_activity_list,
            'dataset_type': current_pkg_dict['type'],
        }
    )


def changes_multiple(package_type=None):
    '''
    Called when a user specifies a range of versions they want to look at
    changes between. Verifies that the range is valid and finds the set of
    activity diffs for the changes in the given version range, then
    re-renders changes.html with the list.
    '''

    new_id = h.get_request_param('new_id')
    old_id = h.get_request_param('old_id')

    context = {
        'model': model, 'session': model.Session,
        'user': g.user, 'auth_user_obj': g.userobj
    }

    # check to ensure that the old activity is actually older than
    # the new activity
    old_activity = get_action('activity_show')(context, {
        'id': old_id,
        'include_data': False})
    new_activity = get_action('activity_show')(context, {
        'id': new_id,
        'include_data': False})

    old_timestamp = old_activity['timestamp']
    new_timestamp = new_activity['timestamp']

    t1 = datetime.strptime(old_timestamp, '%Y-%m-%dT%H:%M:%S.%f')
    t2 = datetime.strptime(new_timestamp, '%Y-%m-%dT%H:%M:%S.%f')

    time_diff = t2 - t1
    # if the time difference is negative, just return the change that put us
    # at the more recent ID we were just looking at
    # TODO: do something better here - go back to the previous page,
    # display a warning that the user can't look at a sequence where
    # the newest item is older than the oldest one, etc
    if time_diff.total_seconds() < 0:
        return changes(h.get_request_param('current_new_id'))

    done = False
    current_id = new_id
    diff_list = []

    while not done:
        try:
            activity_diff = get_action('activity_diff')(
                context, {
                    'id': current_id,
                    'object_type': 'package',
                    'diff_type': 'html'})
        except NotFound as e:
            log.info(
                'Activity not found: {} - {}'.format(str(e), current_id)
            )
            return base.abort(404, _('Activity not found'))
        except NotAuthorized:
            return base.abort(403, _('Unauthorized to view activity data'))

        diff_list.append(activity_diff)

        if activity_diff['activities'][0]['id'] == old_id:
            done = True
        else:
            current_id = activity_diff['activities'][0]['id']

    pkg_id = diff_list[0]['activities'][1]['data']['package']['id']
    current_pkg_dict = get_action('package_show')(context, {'id': pkg_id})
    pkg_activity_list = get_action('package_activity_list')(context, {
        'id': pkg_id,
        'limit': 100})

    return base.render(
        'package/changes.html', {
            'activity_diffs': diff_list,
            'pkg_dict': current_pkg_dict,
            'pkg_activity_list': pkg_activity_list,
            'dataset_type': current_pkg_dict['type'],
        }
    )


def collaborators_read(package_type, id):
    context = {'model': model, 'user': g.user}
    data_dict = {'id': id}

    try:
        check_access('package_collaborator_list', context, data_dict)
        # needed to ckan_extend package/edit_base.html
        pkg_dict = get_action('package_show')(context, data_dict)
    except NotAuthorized:
        message = _('Unauthorized to read collaborators {}').format(id)
        return base.abort(401, message)
    except NotFound:
        return base.abort(404, _('Dataset not found'))

    return base.render('package/collaborators/collaborators.html', {
        'pkg_dict': pkg_dict})


def collaborator_delete(package_type, id, user_id):
    context = {'model': model, 'user': g.user}

    try:
        get_action('package_collaborator_delete')(context, {
            'id': id,
            'user_id': user_id
        })
    except NotAuthorized:
        message = _('Unauthorized to delete collaborators {}').format(id)
        return base.abort(401, _(message))
    except NotFound as e:
        return base.abort(404, _(e.message))

    h.flash_success(_('User removed from collaborators'))

    return h.redirect_to('dataset.collaborators_read', id=id)


class CollaboratorEditView(MethodView):

    def post(self, package_type, id):
        context = {'model': model, 'user': g.user}

        try:
            form_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(request.form))))

            user = get_action('user_show')(
                context, {'id': form_dict['username']}
            )

            data_dict = {
                'id': id,
                'user_id': user['id'],
                'capacity': form_dict['capacity']
            }

            get_action('package_collaborator_create')(
                context, data_dict)

        except dict_fns.DataError:
            return base.abort(400, _('Integrity Error'))
        except NotAuthorized:
            message = _('Unauthorized to edit collaborators {}').format(id)
            return base.abort(401, _(message))
        except NotFound as e:
            h.flash_error(_('User not found'))
            return h.redirect_to('dataset.new_collaborator', id=id)
        except ValidationError as e:
            h.flash_error(e.error_summary)
            return h.redirect_to('dataset.new_collaborator', id=id)
        else:
            h.flash_success(_('User added to collaborators'))

        return h.redirect_to('dataset.collaborators_read', id=id)

    def get(self, package_type, id):
        context = {'model': model, 'user': g.user}
        data_dict = {'id': id}

        try:
            check_access('package_collaborator_list', context, data_dict)
            # needed to ckan_extend package/edit_base.html
            pkg_dict = get_action('package_show')(context, data_dict)
        except NotAuthorized:
            message = 'Unauthorized to read collaborators {}'.format(id)
            return base.abort(401, _(message))
        except NotFound:
            return base.abort(404, _('Resource not found'))

        user = request.params.get('user_id')
        user_capacity = 'member'

        if user:
            collaborators = get_action('package_collaborator_list')(
                context, data_dict)
            for c in collaborators:
                if c['user_id'] == user:
                    user_capacity = c['capacity']
            user = get_action('user_show')(context, {'id': user})

        capacities = []
        if authz.check_config_permission('allow_admin_collaborators'):
            capacities.append({'name': 'admin', 'value': 'admin'})
        capacities.extend([
            {'name': 'editor', 'value': 'editor'},
            {'name': 'member', 'value': 'member'}
        ])

        extra_vars = {
            'capacities': capacities,
            'user_capacity': user_capacity,
            'user': user,
            'pkg_dict': pkg_dict,
        }

        return base.render(
            'package/collaborators/collaborator_new.html', extra_vars)


# deprecated
def history(package_type, id):
    return h.redirect_to('{}.activity'.format(package_type), id=id)


def register_dataset_plugin_rules(blueprint):
    blueprint.add_url_rule('/', view_func=search, strict_slashes=False)
    blueprint.add_url_rule('/new', view_func=CreateView.as_view(str('new')))
    blueprint.add_url_rule('/<id>', view_func=read)
    blueprint.add_url_rule('/resources/<id>', view_func=resources)
    blueprint.add_url_rule(
        '/edit/<id>', view_func=EditView.as_view(str('edit'))
    )
    blueprint.add_url_rule(
        '/delete/<id>', view_func=DeleteView.as_view(str('delete'))
    )
    blueprint.add_url_rule(
        '/follow/<id>', view_func=follow, methods=('POST', )
    )
    blueprint.add_url_rule(
        '/unfollow/<id>', view_func=unfollow, methods=('POST', )
    )
    blueprint.add_url_rule('/followers/<id>', view_func=followers)
    blueprint.add_url_rule(
        '/groups/<id>', view_func=GroupView.as_view(str('groups'))
    )
    blueprint.add_url_rule('/activity/<id>', view_func=activity)
    blueprint.add_url_rule('/changes/<id>', view_func=changes)
    blueprint.add_url_rule('/<id>/history', view_func=history)

    blueprint.add_url_rule('/changes_multiple', view_func=changes_multiple)

    # Duplicate resource create and edit for backward compatibility. Note,
    # we cannot use resource.CreateView directly here, because of
    # circular imports
    blueprint.add_url_rule(
        '/new_resource/<id>',
        view_func=LazyView(
            'ckan.views.resource.CreateView', str('new_resource')
        )
    )

    blueprint.add_url_rule(
        '/<id>/resource_edit/<resource_id>',
        view_func=LazyView(
            'ckan.views.resource.EditView', str('edit_resource')
        )

    )

    if authz.check_config_permission('allow_dataset_collaborators'):
        blueprint.add_url_rule(
            rule='/collaborators/<id>',
            view_func=collaborators_read,
            methods=['GET', ]
        )

        blueprint.add_url_rule(
            rule='/collaborators/<id>/new',
            view_func=CollaboratorEditView.as_view(str('new_collaborator')),
            methods=['GET', 'POST', ]
        )

        blueprint.add_url_rule(
            rule='/collaborators/<id>/delete/<user_id>',
            view_func=collaborator_delete, methods=['POST', ]
        )


register_dataset_plugin_rules(dataset)
