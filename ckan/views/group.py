# encoding: utf-8

import logging
import datetime
from urllib import urlencode

from pylons.i18n import get_lang

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins
import ckan.plugins as plugins
from ckan.common import OrderedDict, c, config, request, _
from flask import Blueprint
import ckan.lib.plugins as lib_plugins

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

log = logging.getLogger(__name__)

group = Blueprint('group', __name__, url_prefix=u'/group')
organization = Blueprint('organization', __name__, url_prefix=u'/organization')

lookup_group_plugin = ckan.lib.plugins.lookup_group_plugin
lookup_group_controller = ckan.lib.plugins.lookup_group_controller


def _index_template(group_type):
    return lookup_group_plugin(group_type).index_template()


def _group_form(group_type=None):
    return lookup_group_plugin(group_type).group_form()


def _form_to_db_schema(group_type=None):
    return lookup_group_plugin(group_type).form_to_db_schema()


def _db_to_form_schema(group_type=None):
    '''This is an interface to manipulate data from the database
    into a format suitable for the form (optional)'''
    return lookup_group_plugin(group_type).db_to_form_schema()


def _setup_template_variables(context, data_dict, group_type=None):
    return lookup_group_plugin(group_type).\
        setup_template_variables(context, data_dict)


def _new_template(group_type):
    return lookup_group_plugin(group_type).new_template()


def _about_template(group_type):
    return lookup_group_plugin(group_type).about_template()


def _read_template(group_type):
    return lookup_group_plugin(group_type).read_template()


def _history_template(group_type):
    return lookup_group_plugin(group_type).history_template()


def _edit_template(group_type):
    return lookup_group_plugin(group_type).edit_template()


def _activity_template(group_type):
    return lookup_group_plugin(group_type).activity_template()


def _admins_template(group_type):
    return lookup_group_plugin(group_type).admins_template()


def _bulk_process_template(group_type):
    return lookup_group_plugin(group_type).bulk_process_template()


# end hooks
def _replace_group_org(string):
    ''' substitute organization for group if this is an org'''
    return string


def _action(action_name):
    ''' select the correct group/org action '''
    return get_action(_replace_group_org(action_name))


def _check_access(action_name, *args, **kw):
    ''' select the correct group/org check_access '''
    return check_access(_replace_group_org(action_name), *args, **kw)


def _render_template(template_name, group_type):
    ''' render the correct group/org template '''
    return base.render(
        _replace_group_org(template_name),
        extra_vars={'group_type': group_type})


def _redirect_to_this_controller(*args, **kw):
    ''' wrapper around redirect_to but it adds in this request's controller
    (so that it works for Organization or other derived controllers)'''
    kw['controller'] = request.environ['pylons.routes_dict']['controller']
    return h.redirect_to(*args, **kw)


def _url_for_this_controller(*args, **kw):
    ''' wrapper around url_for but it adds in this request's controller
    (so that it works for Organization or other derived controllers)'''
    kw['controller'] = request.environ['pylons.routes_dict']['controller']
    return h.url_for(*args, **kw)


def _guess_group_type(expecting_name=False):
    """
    Guess the type of group from the URL.
    * The default url '/group/xyz' returns None
    * group_type is unicode
    * this handles the case where there is a prefix on the URL
    (such as /data/organization)
    """
    # parts = [x for x in request.path.split('/') if x]

    # idx = -1
    # if expecting_name:
    #     idx = -2

    # gt = parts[idx]
    # return gt
    return request.path.split('/')[1]


def index():
    group_type = _guess_group_type()
    page = h.get_page_number(request.params) or 1
    items_per_page = 21

    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'for_view': True,
        'with_private': False
    }

    q = c.q = request.params.get('q', '')
    sort_by = c.sort_by_selected = request.params.get('sort')
    try:
        _check_access('site_read', context)
        _check_access('group_list', context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    # pass user info to context as needed to view private datasets of
    # orgs correctly
    if c.userobj:
        context['user_id'] = c.userobj.id
        context['user_is_admin'] = c.userobj.sysadmin

    try:
        data_dict_global_results = {
            'all_fields': False,
            'q': q,
            'sort': sort_by,
            'type': group_type or 'group',
        }
        global_results = _action('group_list')(context,
                                               data_dict_global_results)
    except ValidationError as e:
        if e.error_dict and e.error_dict.get('message'):
            msg = e.error_dict['message']
        else:
            msg = str(e)
        h.flash_error(msg)
        c.page = h.Page([], 0)
        return base.render(
            _index_template(group_type), extra_vars={'group_type': group_type})

    data_dict_page_results = {
        'all_fields': True,
        'q': q,
        'sort': sort_by,
        'type': group_type or 'group',
        'limit': items_per_page,
        'offset': items_per_page * (page - 1),
        'include_extras': True
    }
    page_results = _action('group_list')(context, data_dict_page_results)

    c.page = h.Page(
        collection=global_results,
        page=page,
        url=h.pager_url,
        items_per_page=items_per_page, )

    c.page.items = page_results
    templ_name = _index_template(group_type)
    vars = dict(group_type=group_type)
    return base.render(templ_name, extra_vars=vars)


def read(id=None, limit=20):
    group_type = _guess_group_type()

    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'schema': _db_to_form_schema(group_type=group_type),
        'for_view': True
    }
    data_dict = {'id': id, 'type': group_type}

    # unicode format (decoded from utf8)
    c.q = request.params.get('q', '')

    try:
        # Do not query for the group datasets when dictizing, as they will
        # be ignored and get requested on the controller anyway
        data_dict['include_datasets'] = False
        c.group_dict = _action('group_show')(context, data_dict)
        c.group = context['group']
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))

    _read(id, limit, group_type)
    return base.render(
        _read_template(c.group_dict['type']),
        extra_vars={'group_type': group_type})


def _read(id, limit, group_type):
    ''' This is common code used by both read and bulk_process'''
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'schema': _db_to_form_schema(group_type=group_type),
        'for_view': True,
        'extras_as_string': True
    }

    q = c.q = request.params.get('q', '')
    # Search within group
    if c.group_dict.get('is_organization'):
        q += ' owner_org:"%s"' % c.group_dict.get('id')
    else:
        q += ' groups:"%s"' % c.group_dict.get('name')

    c.description_formatted = \
        h.render_markdown(c.group_dict.get('description'))

    context['return_query'] = True

    page = h.get_page_number(request.params)

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.params.items() if k != 'page']
    sort_by = request.params.get('sort', None)

    def search_url(params):
        controller = lookup_group_controller(group_type)
        action = 'bulk_process' if c.action == 'bulk_process' else 'read'
        url = h.url_for(controller=controller, action=action, id=id)
        params = [(k, v.encode('utf-8')
                   if isinstance(v, basestring) else str(v))
                  for k, v in params]
        return url + u'?' + urlencode(params)

    def drill_down_url(**by):
        return h.add_url_param(
            alternative_url=None,
            controller='group',
            action='read',
            extras=dict(id=c.group_dict.get('name')),
            new_params=by)

    c.drill_down_url = drill_down_url

    def remove_field(key, value=None, replace=None):
        controller = lookup_group_controller(group_type)
        return h.remove_url_param(
            key,
            value=value,
            replace=replace,
            controller=controller,
            action='read',
            extras=dict(id=c.group_dict.get('name')))

    c.remove_field = remove_field

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append(('page', page))
        return search_url(params)

    try:
        c.fields = []
        c.fields_grouped = {}
        search_extras = {}
        for (param, value) in request.params.items():
            if param not in ['q', 'page', 'sort'] \
                    and len(value) and not param.startswith('_'):
                if not param.startswith('ext_'):
                    c.fields.append((param, value))
                    q += ' %s: "%s"' % (param, value)
                    if param not in c.fields_grouped:
                        c.fields_grouped[param] = [value]
                    else:
                        c.fields_grouped[param].append(value)
                else:
                    search_extras[param] = value

        facets = OrderedDict()

        default_facet_titles = {
            'organization': _('Organizations'),
            'groups': _('Groups'),
            'tags': _('Tags'),
            'res_format': _('Formats'),
            'license_id': _('Licenses')
        }

        for facet in h.facets():
            if facet in default_facet_titles:
                facets[facet] = default_facet_titles[facet]
            else:
                facets[facet] = facet

        # Facet titles
        _update_facet_titles(facets, group_type)

        c.facet_titles = facets

        data_dict = {
            'q': q,
            'fq': '',
            'include_private': True,
            'facet.field': facets.keys(),
            'rows': limit,
            'sort': sort_by,
            'start': (page - 1) * limit,
            'extras': search_extras
        }

        context_ = dict((k, v) for (k, v) in context.items() if k != 'schema')
        query = get_action('package_search')(context_, data_dict)

        c.page = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit)

        c.group_dict['package_count'] = query['count']

        c.search_facets = query['search_facets']
        c.search_facets_limits = {}
        for facet in c.search_facets.keys():
            limit = int(
                request.params.get('_%s_limit' % facet,
                                   config.get('search.facets.default', 10)))
            c.search_facets_limits[facet] = limit
        c.page.items = query['results']

        c.sort_by_selected = sort_by

    except search.SearchError, se:
        log.error('Group search error: %r', se.args)
        c.query_error = True
        c.page = h.Page(collection=[])

    _setup_template_variables(context, {'id': id}, group_type=group_type)


def _update_facet_titles(facets, group_type):
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.group_facets(facets, group_type, None)


def _get_group_dict(id):
    ''' returns the result of group_show action or aborts if there is a
    problem '''
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'for_view': True
    }
    try:
        return _action('group_show')(context, {
            'id': id,
            'include_datasets': False
        })
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))


def _force_reindex(self, grp):
    ''' When the group name has changed, we need to force a reindex
    of the datasets within the group, otherwise they will stop
    appearing on the read page for the group (as they're connected via
    the group name)'''
    group = model.Group.get(grp['name'])
    for dataset in group.packages():
        search.rebuild(dataset.name)


def _save_edit(id, context):
    try:
        data_dict = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.params))))
        context['message'] = data_dict.get('log_message', '')
        data_dict['id'] = id
        context['allow_partial_update'] = True
        group = _action('group_update')(context, data_dict)
        if id != group['name']:
            _force_reindex(group)

        h.redirect_to('%s_read' % group['type'], id=group['name'])
    except (NotFound, NotAuthorized), e:
        base.abort(404, _('Group not found'))
    except dict_fns.DataError:
        base.abort(400, _(u'Integrity Error'))
    except ValidationError, e:
        errors = e.error_dict
        error_summary = e.error_summary
        return edit(id, data_dict, errors, error_summary)


def _save_new(context, group_type=None):
    try:
        data_dict = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.params))))
        data_dict['type'] = group_type or 'group'
        context['message'] = data_dict.get('log_message', '')
        data_dict['users'] = [{'name': c.user, 'capacity': 'admin'}]
        group = _action('group_create')(context, data_dict)

        # Redirect to the appropriate _read route for the type of group
        h.redirect_to(group['type'] + '_read', id=group['name'])
    except (NotFound, NotAuthorized), e:
        base.abort(404, _('Group not found'))
    except dict_fns.DataError:
        base.abort(400, _(u'Integrity Error'))
    except ValidationError, e:
        errors = e.error_dict
        error_summary = e.error_summary
        return new(data_dict, errors, error_summary)


def new(data=None, errors=None, error_summary=None):
    print 'HEEEEEEEEEEEEELOOOOOOOOOOOOOO'
    if data and 'type' in data:
        group_type = data['type']
    else:
        group_type = _guess_group_type(True)
    if data:
        data['type'] = group_type

    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'save': 'save' in request.params,
        'parent': request.params.get('parent', None)
    }
    try:
        _check_access('group_create', context)
    except NotAuthorized:
        base.abort(403, _('Unauthorized to create a group'))

    if context['save'] and not data:
        return _save_new(context, group_type)

    data = data or {}
    if not data.get('image_url', '').startswith('http'):
        data.pop('image_url', None)

    errors = errors or {}
    error_summary = error_summary or {}
    vars = {
        'data': data,
        'errors': errors,
        'error_summary': error_summary,
        'action': 'new',
        'group_type': group_type
    }

    _setup_template_variables(context, data, group_type=group_type)
    c.form = base.render(_group_form(group_type=group_type), extra_vars=vars)
    return base.render(
        _new_template(group_type), extra_vars={'group_type': group_type})


def edit(id, data=None, errors=None, error_summary=None):
    group_type = _guess_group_type()
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'save': 'save' in request.params,
        'for_edit': True,
        'parent': request.params.get('parent', None)
    }
    data_dict = {'id': id, 'include_datasets': False}

    if context['save'] and not data:
        return _save_edit(id, context)

    try:
        data_dict['include_datasets'] = False
        old_data = _action('group_show')(context, data_dict)
        c.grouptitle = old_data.get('title')
        c.groupname = old_data.get('name')
        data = data or old_data
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))

    group = context.get("group")
    c.group = group
    c.group_dict = _action('group_show')(context, data_dict)

    try:
        _check_access('group_update', context)
    except NotAuthorized:
        base.abort(403, _('User %r not authorized to edit %s') % (c.user, id))

    errors = errors or {}
    vars = {
        'data': data,
        'errors': errors,
        'error_summary': error_summary,
        'action': 'edit',
        'group_type': group_type
    }

    _setup_template_variables(context, data, group_type=group_type)
    c.form = base.render(_group_form(group_type), extra_vars=vars)
    return base.render(
        _edit_template(c.group.type), extra_vars={'group_type': group_type})


def activity(id, offset=0):
    '''Render this group's public activity stream page.'''

    group_type = _guess_group_type()
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'for_view': True
    }
    try:
        c.group_dict = _get_group_dict(id)
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))

    try:
        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html
        # template to retrieve later.
        c.group_activity_stream = _action('group_activity_list_html')(
            context, {
                'id': c.group_dict['id'],
                'offset': offset
            })

    except ValidationError as error:
        base.abort(400, error.message)

    return base.render(
        _activity_template(group_type), extra_vars={'group_type': group_type})


def about(id):
    group_type = _guess_group_type()
    context = {'model': model, 'session': model.Session, 'user': c.user}
    c.group_dict = _get_group_dict(id)
    group_type = c.group_dict['type']
    _setup_template_variables(context, {'id': id}, group_type=group_type)
    return base.render(_about_template(group_type),
                       extra_vars={'group_type': group_type})


# Routing
group.add_url_rule(u'/', methods=[u'GET'], view_func=index)
group.add_url_rule(u'/new', methods=[u'GET', u'POST'], view_func=new)
group.add_url_rule(u'/<id>', methods=[u'GET'], view_func=read)
group.add_url_rule(u'/activity/<id>/<offset>', methods=[u'GET'],
                   view_func=activity)
group.add_url_rule(u'/about/<id>', methods=[u'GET'], view_func=about)


organization.add_url_rule(u'/', methods=[u'GET'], view_func=index)
organization.add_url_rule(u'/new', methods=[u'GET', u'POST'], view_func=new)
organization.add_url_rule(u'/<id>', methods=[u'GET'], view_func=read)
organization.add_url_rule(u'/activity/<id>/<offset>', methods=[u'GET'], 
                          view_func=activity)
organization.add_url_rule(u'/about/<id>', methods=[u'GET'], view_func=about)
