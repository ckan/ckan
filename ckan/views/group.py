# encoding: utf-8

import logging
import re
from collections import OrderedDict

import six
from six import string_types
from six.moves.urllib.parse import urlencode
from datetime import datetime

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins as lib_plugins
import ckan.plugins as plugins
from ckan.common import g, config, request, _
from ckan.views.home import CACHE_PARAMETERS
from ckan.views.dataset import _get_search_details

from flask import Blueprint
from flask.views import MethodView


NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

log = logging.getLogger(__name__)

lookup_group_plugin = lib_plugins.lookup_group_plugin
lookup_group_controller = lib_plugins.lookup_group_controller
lookup_group_blueprint = lib_plugins.lookup_group_blueprints

is_org = False


def _get_group_template(template_type, group_type=None):
    group_plugin = lookup_group_plugin(group_type)
    method = getattr(group_plugin, template_type)
    try:
        return method(group_type)
    except TypeError as err:
        if 'takes 1' not in str(err) and 'takes exactly 1' not in str(err):
            raise
        return method()


def _db_to_form_schema(group_type=None):
    '''This is an interface to manipulate data from the database
     into a format suitable for the form (optional)'''
    return lookup_group_plugin(group_type).db_to_form_schema()


def _setup_template_variables(context, data_dict, group_type=None):
    if 'type' not in data_dict:
        data_dict['type'] = group_type
    return lookup_group_plugin(group_type).\
        setup_template_variables(context, data_dict)


def _replace_group_org(string):
    ''' substitute organization for group if this is an org'''
    if is_org:
        return re.sub('^group', 'organization', string)
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


def _force_reindex(grp):
    ''' When the group name has changed, we need to force a reindex
    of the datasets within the group, otherwise they will stop
    appearing on the read page for the group (as they're connected via
    the group name)'''
    group = model.Group.get(grp['name'])
    for dataset in group.packages():
        search.rebuild(dataset.name)


def _guess_group_type(expecting_name=False):
    """
            Guess the type of group from the URL.
            * The default url '/group/xyz' returns None
            * group_type is unicode
            * this handles the case where there is a prefix on the URL
              (such as /data/organization)
        """
    parts = [x for x in request.path.split('/') if x]

    idx = 0
    if expecting_name:
        idx = -1

    gt = parts[idx]

    return gt


def set_org(is_organization):
    global is_org
    is_org = is_organization


def index(group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    page = h.get_page_number(request.params) or 1
    items_per_page = int(config.get('ckan.datasets_per_page', 20))

    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True,
        'with_private': False
    }

    try:
        _check_access('site_read', context)
        _check_access('group_list', context)
    except NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    q = request.params.get('q', '')
    sort_by = request.params.get('sort')

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.q = q
    g.sort_by_selected = sort_by

    extra_vars["q"] = q
    extra_vars["sort_by_selected"] = sort_by

    # pass user info to context as needed to view private datasets of
    # orgs correctly
    if g.userobj:
        context['user_id'] = g.userobj.id
        context['user_is_admin'] = g.userobj.sysadmin

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
        extra_vars["page"] = h.Page([], 0)
        extra_vars["group_type"] = group_type
        return base.render(
            _get_group_template('index_template', group_type), extra_vars)

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

    extra_vars["page"] = h.Page(
        collection=global_results,
        page=page,
        url=h.pager_url,
        items_per_page=items_per_page, )

    extra_vars["page"].items = page_results
    extra_vars["group_type"] = group_type

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.page = extra_vars["page"]
    return base.render(
        _get_group_template('index_template', group_type), extra_vars)


def _read(id, limit, group_type):
    ''' This is common code used by both read and bulk_process'''
    extra_vars = {}
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'schema': _db_to_form_schema(group_type=group_type),
        'for_view': True,
        'extras_as_string': True
    }

    q = request.params.get('q', '')

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.q = q

    # Search within group
    if g.group_dict.get('is_organization'):
        fq = ' owner_org:"%s"' % g.group_dict.get('id')
    else:
        fq = ' groups:"%s"' % g.group_dict.get('name')

    extra_vars["q"] = q

    g.description_formatted = \
        h.render_markdown(g.group_dict.get('description'))

    context['return_query'] = True

    page = h.get_page_number(request.params)

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.params.items(multi=True)
                     if k != 'page']
    sort_by = request.params.get('sort', None)

    def search_url(params):
        action = 'bulk_process' if getattr(
            g, 'action', '') == 'bulk_process' else 'read'
        url = h.url_for('.'.join([group_type, action]), id=id)
        params = [(k, v.encode('utf-8')
                   if isinstance(v, string_types) else str(v))
                  for k, v in params]
        return url + '?' + urlencode(params)

    def drill_down_url(**by):
        return h.add_url_param(
            alternative_url=None,
            controller=group_type,
            action='read',
            extras=dict(id=g.group_dict.get('name')),
            new_params=by)

    extra_vars["drill_down_url"] = drill_down_url

    def remove_field(key, value=None, replace=None):
        controller = lookup_group_controller(group_type)
        return h.remove_url_param(
            key,
            value=value,
            replace=replace,
            controller=controller,
            action='read',
            extras=dict(id=g.group_dict.get('name')))

    extra_vars["remove_field"] = remove_field

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append(('page', page))
        return search_url(params)

    details = _get_search_details()
    extra_vars['fields'] = details['fields']
    extra_vars['fields_grouped'] = details['fields_grouped']
    fq += details['fq']
    search_extras = details['search_extras']

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.fields = extra_vars['fields']
    g.fields_grouped = extra_vars['fields_grouped']

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
        'license_id': _('Licenses')
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    facets = _update_facet_titles(facets, group_type)

    extra_vars["facet_titles"] = facets

    data_dict = {
        'q': q,
        'fq': fq,
        'include_private': True,
        'facet.field': list(facets.keys()),
        'rows': limit,
        'sort': sort_by,
        'start': (page - 1) * limit,
        'extras': search_extras
    }

    context_ = dict((k, v) for (k, v) in context.items() if k != 'schema')
    try:
        query = get_action('package_search')(context_, data_dict)
    except search.SearchError as se:
        log.error('Group search error: %r', se.args)
        extra_vars["query_error"] = True
        extra_vars["page"] = h.Page(collection=[])
    else:
        extra_vars["page"] = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit)

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.group_dict['package_count'] = query['count']

        extra_vars["search_facets"] = g.search_facets = query['search_facets']
        extra_vars["search_facets_limits"] = g.search_facets_limits = {}
        for facet in g.search_facets.keys():
            limit = int(
                request.params.get('_%s_limit' % facet,
                                   config.get('search.facets.default', 10)))
            g.search_facets_limits[facet] = limit
        extra_vars["page"].items = query['results']

        extra_vars["sort_by_selected"] = sort_by

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.facet_titles = facets
    g.page = extra_vars["page"]

    extra_vars["group_type"] = group_type
    _setup_template_variables(context, {'id': id}, group_type=group_type)
    return extra_vars


def _update_facet_titles(facets, group_type):
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.group_facets(facets, group_type, None)
    return facets


def _get_group_dict(id, group_type):
    ''' returns the result of group_show action or aborts if there is a
    problem '''
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True
    }
    try:
        return _action('group_show')(context, {
            'id': id,
            'include_datasets': False
        })
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))


def read(group_type, is_organization, id=None, limit=20):
    extra_vars = {}
    set_org(is_organization)
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'schema': _db_to_form_schema(group_type=group_type),
        'for_view': True
    }
    data_dict = {'id': id, 'type': group_type}

    # unicode format (decoded from utf8)
    q = request.params.get('q', '')

    extra_vars["q"] = q

    try:
        # Do not query for the group datasets when dictizing, as they will
        # be ignored and get requested on the controller anyway
        data_dict['include_datasets'] = False

        # Do not query group members as they aren't used in the view
        data_dict['include_users'] = False

        group_dict = _action('group_show')(context, data_dict)
        group = context['group']
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))

    # if the user specified a group id, redirect to the group name
    if data_dict['id'] == group_dict['id'] and \
            data_dict['id'] != group_dict['name']:

        url_with_name = h.url_for('{}.read'.format(group_type),
                                  id=group_dict['name'])

        return h.redirect_to(
            h.add_url_param(alternative_url=url_with_name))

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.q = q
    g.group_dict = group_dict
    g.group = group

    extra_vars = _read(id, limit, group_type)

    extra_vars["group_type"] = group_type
    extra_vars["group_dict"] = group_dict

    return base.render(
        _get_group_template('read_template', g.group_dict['type']),
        extra_vars)


def activity(id, group_type, is_organization, offset=0):
    '''Render this group's public activity stream page.'''
    extra_vars = {}
    set_org(is_organization)
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True
    }
    try:
        group_dict = _get_group_dict(id, group_type)
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))

    try:
        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html
        # template to retrieve later.
        extra_vars["activity_stream"] = \
            _action('organization_activity_list'
                    if group_dict.get('is_organization')
                    else 'group_activity_list')(
            context, {
                'id': group_dict['id'],
                'offset': offset
            })

    except ValidationError as error:
        base.abort(400, error.message)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.group_activity_stream = extra_vars["activity_stream"]
    g.group_dict = group_dict

    extra_vars["group_type"] = group_type
    extra_vars["group_dict"] = group_dict
    extra_vars["id"] = id
    return base.render(
        _get_group_template('activity_template', group_type), extra_vars)


def changes(id, group_type, is_organization):
    '''
    Shows the changes to an organization in one particular activity stream
    item.
    '''
    set_org(is_organization)
    extra_vars = {}
    activity_id = id
    context = {
        'model': model, 'session': model.Session,
        'user': g.user, 'auth_user_obj': g.userobj
    }
    try:
        activity_diff = get_action('activity_diff')(
            context, {'id': activity_id, 'object_type': 'group',
                      'diff_type': 'html'})
    except NotFound as e:
        log.info('Activity not found: {} - {}'.format(str(e), activity_id))
        return base.abort(404, _('Activity not found'))
    except NotAuthorized:
        return base.abort(403, _('Unauthorized to view activity data'))

    # 'group_dict' needs to go to the templates for page title & breadcrumbs.
    # Use the current version of the package, in case the name/title have
    # changed, and we need a link to it which works
    group_id = activity_diff['activities'][1]['data']['group']['id']
    current_group_dict = get_action(group_type + '_show')(
        context, {'id': group_id})
    group_activity_list = get_action(group_type + '_activity_list')(
        context, {
            'id': group_id,
            'limit': 100
        }
    )

    extra_vars = {
        'activity_diffs': [activity_diff],
        'group_dict': current_group_dict,
        'group_activity_list': group_activity_list,
        'group_type': current_group_dict['type'],
    }

    return base.render(_replace_group_org('group/changes.html'), extra_vars)


def changes_multiple(is_organization, group_type=None):
    '''
    Called when a user specifies a range of versions they want to look at
    changes between. Verifies that the range is valid and finds the set of
    activity diffs for the changes in the given version range, then
    re-renders changes.html with the list.
    '''
    set_org(is_organization)
    extra_vars = {}
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
                    'object_type': 'group',
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

    group_id = diff_list[0]['activities'][1]['data']['group']['id']
    current_group_dict = get_action(group_type + '_show')(
        context, {'id': group_id})
    group_activity_list = get_action(group_type + '_activity_list')(context, {
        'id': group_id,
        'limit': 100})

    extra_vars = {
        'activity_diffs': diff_list,
        'group_dict': current_group_dict,
        'group_activity_list': group_activity_list,
        'group_type': current_group_dict['type'],
    }

    return base.render(_replace_group_org('group/changes.html'), extra_vars)


def about(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    context = {'model': model, 'session': model.Session, 'user': g.user}
    group_dict = _get_group_dict(id, group_type)
    group_type = group_dict['type']
    _setup_template_variables(context, {'id': id}, group_type=group_type)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.group_dict = group_dict
    g.group_type = group_type

    extra_vars = {"group_dict": group_dict,
                  "group_type": group_type}

    return base.render(
        _get_group_template('about_template', group_type), extra_vars)


def members(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    context = {'model': model, 'session': model.Session, 'user': g.user}

    try:
        data_dict = {'id': id}
        check_access('group_edit_permissions', context, data_dict)
        members = get_action('member_list')(context, {
            'id': id,
            'object_type': 'user'
        })
        data_dict['include_datasets'] = False
        group_dict = _action('group_show')(context, data_dict)
    except NotFound:
        base.abort(404, _('Group not found'))
    except NotAuthorized:
        base.abort(403,
                   _('User %r not authorized to edit members of %s') %
                   (g.user, id))

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.members = members
    g.group_dict = group_dict

    extra_vars = {
        "members": members,
        "group_dict": group_dict,
        "group_type": group_type
    }
    return base.render(_replace_group_org('group/members.html'), extra_vars)


def member_delete(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    if 'cancel' in request.params:
        return h.redirect_to('{}.members'.format(group_type), id=id)

    context = {'model': model, 'session': model.Session, 'user': g.user}

    try:
        _check_access('group_member_delete', context, {'id': id})
    except NotAuthorized:
        base.abort(403, _('Unauthorized to delete group %s members') % '')

    try:
        user_id = request.params.get('user')
        if request.method == 'POST':
            _action('group_member_delete')(context, {
                'id': id,
                'user_id': user_id
            })
            h.flash_notice(_('Group member has been deleted.'))
            return h.redirect_to('{}.members'.format(group_type), id=id)
        user_dict = _action('group_show')(context, {'id': user_id})

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.user_dict = user_dict
        g.user_id = user_id
        g.group_id = id

    except NotAuthorized:
        base.abort(403, _('Unauthorized to delete group %s members') % '')
    except NotFound:
        base.abort(404, _('Group not found'))
    extra_vars = {
        "user_id": user_id,
        "user_dict": user_dict,
        "group_id": id
    }
    return base.render(_replace_group_org('group/confirm_delete_member.html'),
                       extra_vars)


# deprecated
def history(id, group_type, is_organization):
    return h.redirect_to('group.activity', id=id)


def follow(id, group_type, is_organization):
    '''Start following this group.'''
    set_org(is_organization)
    context = {'model': model, 'session': model.Session, 'user': g.user}
    data_dict = {'id': id}
    try:
        get_action('follow_group')(context, data_dict)
        group_dict = get_action('group_show')(context, data_dict)
        h.flash_success(
            _("You are now following {0}").format(group_dict['title']))

        id = group_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except NotAuthorized as e:
        h.flash_error(e.message)
    return h.redirect_to('group.read', id=id)


def unfollow(id, group_type, is_organization):
    '''Stop following this group.'''
    set_org(is_organization)
    context = {'model': model, 'session': model.Session, 'user': g.user}
    data_dict = {'id': id}
    try:
        get_action('unfollow_group')(context, data_dict)
        group_dict = get_action('group_show')(context, data_dict)
        h.flash_success(
            _("You are no longer following {0}").format(group_dict['title']))
        id = group_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except (NotFound, NotAuthorized) as e:
        error_message = e.message
        h.flash_error(error_message)
    return h.redirect_to('group.read', id=id)


def followers(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    context = {'model': model, 'session': model.Session, 'user': g.user}
    group_dict = _get_group_dict(id, group_type)
    try:
        followers = \
            get_action('group_follower_list')(context, {'id': id})
    except NotAuthorized:
        base.abort(403, _('Unauthorized to view followers %s') % '')

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.group_dict = group_dict
    g.followers = followers

    extra_vars = {
        "group_dict": group_dict,
        "group_type": group_type,
        "followers": followers
    }
    return base.render('group/followers.html', extra_vars)


def admins(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    group_dict = _get_group_dict(id, group_type)
    admins = authz.get_group_or_org_admin_ids(id)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.group_dict = group_dict
    g.admins = admins

    extra_vars = {
        "group_dict": group_dict,
        'group_type': group_type,
        "admins": admins
    }

    return base.render(
        _get_group_template('admins_template', group_dict['type']),
        extra_vars)


class BulkProcessView(MethodView):
    ''' Bulk process view'''

    def _prepare(self, group_type, id=None):

        # check we are org admin

        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'schema': _db_to_form_schema(group_type=group_type),
            'for_view': True,
            'extras_as_string': True
        }
        return context

    def get(self, id, group_type, is_organization):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare(group_type, id)
        data_dict = {'id': id, 'type': group_type}
        data_dict['include_datasets'] = False
        try:
            group_dict = _action('group_show')(context, data_dict)
            group = context['group']
        except NotFound:
            base.abort(404, _('Group not found'))

        if not group_dict['is_organization']:
            # FIXME: better error
            raise Exception('Must be an organization')

        # If no action then just show the datasets
        limit = 500
        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.group_dict = group_dict
        g.group = group
        extra_vars = _read(id, limit, group_type)
        g.packages = g.page.items

        extra_vars = {
            "group_dict": group_dict,
            "group": group,
            "page": g.page,
            "packages": g.page.items,
            'group_type': group_type
        }

        return base.render(
            _get_group_template('bulk_process_template', group_type),
            extra_vars)

    def post(self, id, group_type, is_organization, data=None):
        set_org(is_organization)
        context = self._prepare(group_type)
        data_dict = {'id': id, 'type': group_type}
        try:
            check_access('bulk_update_public', context, {'org_id': id})
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = False
            group_dict = _action('group_show')(context, data_dict)
            group = context['group']
        except NotFound:
            group_label = h.humanize_entity_type(
                'organization' if is_organization else 'group',
                group_type,
                'default label') or _(
                    'Organization' if is_organization else 'Group')
            base.abort(404, _('{} not found'.format(group_label)))
        except NotAuthorized:
            base.abort(403,
                       _('User %r not authorized to edit %s') % (g.user, id))

        if not group_dict['is_organization']:
            # FIXME: better error
            raise Exception('Must be an organization')

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.group_dict = group_dict
        g.group = group

        # use different form names so that ie7 can be detected
        form_names = set([
            "bulk_action.public",
            "bulk_action.delete",
            "bulk_action.private"
        ])
        actions_in_form = set(request.form.keys())
        actions = form_names.intersection(actions_in_form)
        # ie7 puts all buttons in form params but puts submitted one twice

        for key, value in six.iteritems(request.form.to_dict()):
            if value in ['private', 'public']:
                action = key.split('.')[-1]
                break
        else:
            # normal good browser form submission
            action = actions.pop().split('.')[-1]

        # process the action first find the datasets to perform the action on.
        # they are prefixed by dataset_ in the form data
        datasets = []
        for param in request.form:
            if param.startswith('dataset_'):
                datasets.append(param[8:])

        action_functions = {
            'private': 'bulk_update_private',
            'public': 'bulk_update_public',
            'delete': 'bulk_update_delete',
        }

        data_dict = {'datasets': datasets, 'org_id': group_dict['id']}

        try:
            get_action(action_functions[action])(context, data_dict)
        except NotAuthorized:
            base.abort(403, _('Not authorized to perform bulk update'))
        return h.redirect_to('{}.bulk_process'.format(group_type), id=id)


class CreateGroupView(MethodView):
    '''Create group view '''

    def _prepare(self, data=None):
        if data and 'type' in data:
            group_type = data['type']
        else:
            group_type = _guess_group_type()
        if data:
            data['type'] = group_type

        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'save': 'save' in request.params,
            'parent': request.params.get('parent', None),
            'group_type': group_type
        }

        try:
            _check_access('group_create', context)
        except NotAuthorized:
            base.abort(403, _('Unauthorized to create a group'))

        return context

    def post(self, group_type, is_organization):
        set_org(is_organization)
        context = self._prepare()
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
            data_dict.update(clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
            ))
            data_dict['type'] = group_type or 'group'
            context['message'] = data_dict.get('log_message', '')
            data_dict['users'] = [{'name': g.user, 'capacity': 'admin'}]
            group = _action('group_create')(context, data_dict)

        except (NotFound, NotAuthorized) as e:
            base.abort(404, _('Group not found'))
        except dict_fns.DataError:
            base.abort(400, _('Integrity Error'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(group_type, is_organization,
                            data_dict, errors, error_summary)

        return h.redirect_to(group['type'] + '.read', id=group['name'])

    def get(self, group_type, is_organization,
            data=None, errors=None, error_summary=None):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare()
        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.args, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )

        if not data.get('image_url', '').startswith('http'):
            data.pop('image_url', None)
        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {
            'data': data,
            'errors': errors,
            'error_summary': error_summary,
            'action': 'new',
            'group_type': group_type
        }
        _setup_template_variables(
            context, data, group_type=group_type)
        form = base.render(
            _get_group_template('group_form', group_type), extra_vars)

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.form = form

        extra_vars["form"] = form
        return base.render(
            _get_group_template('new_template', group_type), extra_vars)


class EditGroupView(MethodView):
    ''' Edit group view'''

    def _prepare(self, id, is_organization, data=None):
        data_dict = {'id': id, 'include_datasets': False}

        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'save': 'save' in request.params,
            'for_edit': True,
            'parent': request.params.get('parent', None),
            'id': id
        }

        try:
            group = _action('group_show')(context, data_dict)
            check_access('group_update', context)
        except NotAuthorized:
            base.abort(403, _('Unauthorized to create a group'))
        except NotFound:
            base.abort(404, _('Group not found'))

        return context

    def post(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id, is_organization)
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
            data_dict.update(clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
            ))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = context['id']
            context['allow_partial_update'] = True
            group = _action('group_update')(context, data_dict)
            if id != group['name']:
                _force_reindex(group)

        except (NotFound, NotAuthorized) as e:
            base.abort(404, _('Group not found'))
        except dict_fns.DataError:
            base.abort(400, _('Integrity Error'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, group_type, is_organization,
                            data_dict, errors, error_summary)
        return h.redirect_to(group['type'] + '.read', id=group['name'])

    def get(self, id, group_type, is_organization,
            data=None, errors=None, error_summary=None):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare(id, is_organization)
        data_dict = {'id': id, 'include_datasets': False}
        try:
            group_dict = _action('group_show')(context, data_dict)
        except (NotFound, NotAuthorized):
            base.abort(404, _('Group not found'))
        data = data or group_dict
        errors = errors or {}
        extra_vars = {
            'data': data,
            "group_dict": group_dict,
            'errors': errors,
            'error_summary': error_summary,
            'action': 'edit',
            'group_type': group_type
        }

        _setup_template_variables(context, data, group_type=group_type)
        form = base.render(
            _get_group_template('group_form', group_type), extra_vars)

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.grouptitle = group_dict.get('title')
        g.groupname = group_dict.get('name')
        g.data = data
        g.group_dict = group_dict

        extra_vars["form"] = form
        return base.render(
            _get_group_template('edit_template', group_type), extra_vars)


class DeleteGroupView(MethodView):
    '''Delete group view '''

    def _prepare(self, id=None):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
        }
        try:
            _check_access('group_delete', context, {'id': id})
        except NotAuthorized:
            base.abort(403, _('Unauthorized to delete group %s') % '')
        return context

    def post(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id)
        try:
            _action('group_delete')(context, {'id': id})
            group_label = h.humanize_entity_type(
                'group',
                group_type,
                'has been deleted') or _('Group')
            h.flash_notice(
                _('%s has been deleted.') % _(group_label))
        except NotAuthorized:
            base.abort(403, _('Unauthorized to delete group %s') % '')
        except NotFound:
            base.abort(404, _('Group not found'))
        except ValidationError as e:
            h.flash_error(e.error_dict['message'])
            return h.redirect_to('{}.read'.format(group_type), id=id)

        return h.redirect_to('{}.index'.format(group_type))

    def get(self, group_type, is_organization, id=None):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare(id)
        group_dict = _action('group_show')(context, {'id': id})
        if 'cancel' in request.params:
            return h.redirect_to('{}.edit'.format(group_type), id=id)

        # TODO: Remove
        g.group_dict = group_dict
        extra_vars = {
            "group_dict": group_dict,
            "group_type": group_type
        }
        return base.render(_replace_group_org('group/confirm_delete.html'),
                           extra_vars)


class MembersGroupView(MethodView):
    '''New members group view'''

    def _prepare(self, id=None):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user
        }
        try:
            _check_access('group_member_create', context, {'id': id})
        except NotAuthorized:
            base.abort(403,
                       _('Unauthorized to create group %s members') % '')

        return context

    def post(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id)
        data_dict = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
        data_dict['id'] = id

        email = data_dict.get('email')

        if email:
            user_data_dict = {
                'email': email,
                'group_id': data_dict['id'],
                'role': data_dict['role']
            }
            del data_dict['email']
            user_dict = _action('user_invite')(context, user_data_dict)
            data_dict['username'] = user_dict['name']

        try:
            group_dict = _action('group_member_create')(context, data_dict)
        except NotAuthorized:
            base.abort(403, _('Unauthorized to add member to group %s') % '')
        except NotFound:
            base.abort(404, _('Group not found'))
        except ValidationError as e:
            h.flash_error(e.error_summary)
            return h.redirect_to('{}.member_new'.format(group_type), id=id)

        # TODO: Remove
        g.group_dict = group_dict

        return h.redirect_to('{}.members'.format(group_type), id=id)

    def get(self, group_type, is_organization, id=None):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare(id)
        user = request.params.get('user')
        data_dict = {'id': id}
        data_dict['include_datasets'] = False
        group_dict = _action('group_show')(context, data_dict)
        roles = _action('member_roles_list')(context, {
            'group_type': group_type
        })
        user_dict = {}
        if user:
            user_dict = get_action('user_show')(context, {'id': user})
            user_role =\
                authz.users_role_for_group_or_org(id, user) or 'member'
            # TODO: Remove
            g.user_dict = user_dict
            extra_vars["user_dict"] = user_dict
        else:
            user_role = 'member'

        # TODO: Remove
        g.group_dict = group_dict
        g.roles = roles
        g.user_role = user_role

        extra_vars.update({
            "group_dict": group_dict,
            "roles": roles,
            "user_role": user_role,
            "group_type": group_type,
            "user_dict": user_dict
        })
        return base.render(_replace_group_org('group/member_new.html'),
                           extra_vars)


group = Blueprint('group', __name__, url_prefix='/group',
                  url_defaults={'group_type': 'group',
                                'is_organization': False})
organization = Blueprint('organization', __name__,
                         url_prefix='/organization',
                         url_defaults={'group_type': 'organization',
                                       'is_organization': True})


def register_group_plugin_rules(blueprint):
    actions = [
        'member_delete', 'history', 'followers', 'follow',
        'unfollow', 'admins', 'activity'
    ]
    blueprint.add_url_rule('/', view_func=index, strict_slashes=False)
    blueprint.add_url_rule(
        '/new',
        methods=['GET', 'POST'],
        view_func=CreateGroupView.as_view(str('new')))
    blueprint.add_url_rule('/<id>', methods=['GET'], view_func=read)
    blueprint.add_url_rule(
        '/edit/<id>', view_func=EditGroupView.as_view(str('edit')))
    blueprint.add_url_rule(
        '/activity/<id>/<int:offset>', methods=['GET'], view_func=activity)
    blueprint.add_url_rule('/about/<id>', methods=['GET'], view_func=about)
    blueprint.add_url_rule(
        '/members/<id>', methods=['GET', 'POST'], view_func=members)
    blueprint.add_url_rule(
        '/member_new/<id>',
        view_func=MembersGroupView.as_view(str('member_new')))
    blueprint.add_url_rule(
        '/bulk_process/<id>',
        view_func=BulkProcessView.as_view(str('bulk_process')))
    blueprint.add_url_rule(
        '/delete/<id>',
        methods=['GET', 'POST'],
        view_func=DeleteGroupView.as_view(str('delete')))
    for action in actions:
        blueprint.add_url_rule(
            '/{0}/<id>'.format(action),
            methods=['GET', 'POST'],
            view_func=globals()[action])
    blueprint.add_url_rule('/changes/<id>', view_func=changes)
    blueprint.add_url_rule(
        '/changes_multiple',
        view_func=changes_multiple)


register_group_plugin_rules(group)
register_group_plugin_rules(organization)
