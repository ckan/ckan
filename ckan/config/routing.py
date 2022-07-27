# encoding: utf-8

"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at https://routes.readthedocs.io/en/latest/

"""
import re

from routes.mapper import SubMapper, Mapper as _Mapper

import ckan.plugins as p
from ckan.common import config

named_routes = {}


class Mapper(_Mapper):
    ''' This Mapper allows us to intercept the connect calls used by routes
    so that we can collect named routes and later use them to create links
    via some helper functions like build_nav(). '''

    def connect(self, *args, **kw):
        '''Connect a new route, storing any named routes for later.

        This custom connect() method wraps the standard connect() method,
        and additionally saves any named routes that are connected in a dict
        ckan.routing.named_routes, which ends up being accessible via the
        Pylons config as config['routes.named_routes'].

        Also takes some additional params:

        :param ckan_icon: name of the icon to be associated with this route,
            e.g. 'group', 'time'. Available icons are listed here:
            http://fortawesome.github.io/Font-Awesome/3.2.1/icons/
        :type ckan_icon: string
        :param highlight_actions: space-separated list of controller actions
            that should be treated as the same as this named route for menu
            highlighting purposes, e.g. 'index search'
        :type highlight_actions: string

        '''

        ckan_icon = kw.pop('ckan_icon', None)
        highlight_actions = kw.pop('highlight_actions', kw.get('action', ''))
        ckan_core = kw.pop('ckan_core', None)
        out = _Mapper.connect(self, *args, **kw)
        route = self.matchlist[-1]
        if ckan_core is not None:
            route._ckan_core = ckan_core
        if len(args) == 1 or args[0].startswith('_redirect_'):
            return out
        # we have a named route
        needed = []
        matches = re.findall('\{([^:}]*)(\}|:)', args[1])
        for match in matches:
            needed.append(match[0])
        route_data = {
            'icon': ckan_icon,
            # needed lists the names of the parameters that need defining
            # for the route to be generated
            'needed': needed,
            'controller': kw.get('controller'),
            'action': kw.get('action', ''),
            'highlight_actions': highlight_actions
        }
        named_routes[args[0]] = route_data
        return out


def make_map():
    """Create, configure and return the routes Mapper"""
    # import controllers here rather than at root level because
    # pylons config is initialised by this point.

    # Helpers to reduce code clutter
    GET = dict(method=['GET'])
    PUT = dict(method=['PUT'])
    POST = dict(method=['POST'])
    DELETE = dict(method=['DELETE'])
    GET_POST = dict(method=['GET', 'POST'])
    PUT_POST = dict(method=['PUT', 'POST'])
    PUT_POST_DELETE = dict(method=['PUT', 'POST', 'DELETE'])
    OPTIONS = dict(method=['OPTIONS'])

    import ckan.lib.plugins as lib_plugins
    lib_plugins.reset_package_plugins()

    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False
    map.explicit = True

    # CUSTOM ROUTES HERE
    for plugin in p.PluginImplementations(p.IRoutes):
        map = plugin.before_map(map)

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved.
    map.connect('/error/{action}', controller='error', ckan_core=True)
    map.connect('/error/{action}/{id}', controller='error', ckan_core=True)

    map.connect('*url', controller='home', action='cors_options',
                conditions=OPTIONS, ckan_core=True)

    # Mark all routes added from extensions on the `before_map` extension point
    # as non-core
    for route in map.matchlist:
        if not hasattr(route, '_ckan_core'):
            route._ckan_core = False

    map.connect('invite', '/__invite__/', controller='partyline', action='join_party')

    map.connect('home', '/', controller='home', action='index')
    map.connect('about', '/about', controller='home', action='about')

    # CKAN API versioned.
    register_list = [
        'package',
        'dataset',
        'resource',
        'tag',
        'group',
        'revision',
        'licenses',
        'rating',
        'user',
        'activity'
    ]
    register_list_str = '|'.join(register_list)

    # /api ver 3 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/3|}',
                   ver='/3') as m:
        m.connect('/action/{logic_function}', action='action',
                  conditions=GET_POST)

    # /api ver 1, 2, 3 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|/3|}',
                   ver='/1') as m:
        m.connect('/search/{register}', action='search')

    # /api ver 1, 2 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|}',
                   ver='/1') as m:
        m.connect('/tag_counts', action='tag_counts')
        m.connect('/rest', action='index')
        m.connect('/qos/throughput/', action='throughput', conditions=GET)

    # /api/rest ver 1, 2 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|}',
                   ver='/1', requirements=dict(register=register_list_str)
                   ) as m:

        m.connect('/rest/{register}', action='list', conditions=GET)
        m.connect('/rest/{register}', action='create', conditions=POST)
        m.connect('/rest/{register}/{id}', action='show', conditions=GET)
        m.connect('/rest/{register}/{id}', action='update', conditions=PUT)
        m.connect('/rest/{register}/{id}', action='update', conditions=POST)
        m.connect('/rest/{register}/{id}', action='delete', conditions=DELETE)
        m.connect('/rest/{register}/{id}/:subregister', action='list',
                  conditions=GET)
        m.connect('/rest/{register}/{id}/:subregister', action='create',
                  conditions=POST)
        m.connect('/rest/{register}/{id}/:subregister/{id2}', action='create',
                  conditions=POST)
        m.connect('/rest/{register}/{id}/:subregister/{id2}', action='show',
                  conditions=GET)
        m.connect('/rest/{register}/{id}/:subregister/{id2}', action='update',
                  conditions=PUT)
        m.connect('/rest/{register}/{id}/:subregister/{id2}', action='delete',
                  conditions=DELETE)

    # /api/util ver 1, 2 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|}',
                   ver='/1') as m:
        m.connect('/util/user/autocomplete', action='user_autocomplete')
        m.connect('/util/is_slug_valid', action='is_slug_valid',
                  conditions=GET)
        m.connect('/util/dataset/autocomplete', action='dataset_autocomplete',
                  conditions=GET)
        m.connect('/util/tag/autocomplete', action='tag_autocomplete',
                  conditions=GET)
        m.connect('/util/resource/format_autocomplete',
                  action='format_autocomplete', conditions=GET)
        m.connect('/util/resource/format_icon',
                  action='format_icon', conditions=GET)
        m.connect('/util/group/autocomplete', action='group_autocomplete')
        m.connect('/util/organization/autocomplete', action='organization_autocomplete',
                  conditions=GET)
        m.connect('/util/markdown', action='markdown')
        m.connect('/util/dataset/munge_name', action='munge_package_name')
        m.connect('/util/dataset/munge_title_to_name',
                  action='munge_title_to_package_name')
        m.connect('/util/tag/munge', action='munge_tag')
        m.connect('/util/status', action='status')
        m.connect('/util/snippet/{snippet_path:.*}', action='snippet')
        m.connect('/i18n/{lang}', action='i18n_js_translations')

    ###########
    ## /END API
    ###########

    map.redirect('/packages', '/dataset')
    map.redirect('/packages/{url:.*}', '/dataset/{url}')
    map.redirect('/package', '/dataset')
    map.redirect('/package/{url:.*}', '/dataset/{url}')

    with SubMapper(map, controller='package') as m:
        m.connect('search', '/dataset', action='search',
                  highlight_actions='index search')
        m.connect('add dataset', '/dataset/new', action='new')
        m.connect('/dataset/{action}',
                  requirements=dict(action='|'.join([
                      'list',
                      'autocomplete',
                      'search'
                  ])))

        m.connect('/dataset/{action}/{id}/{revision}', action='read_ajax',
                  requirements=dict(action='|'.join([
                      'read',
                      'edit',
                      'history',
                  ])))
        m.connect('/dataset/{action}/{id}',
                  requirements=dict(action='|'.join([
                      'new_resource',
                      'history',
                      'read_ajax',
                      'history_ajax',
                      'follow',
                      'activity',
                      'groups',
                      'unfollow',
                      'delete',
                      'api_data',
                  ])))
        m.connect('dataset_edit', '/dataset/edit/{id}', action='edit',
                  ckan_icon='pencil-square-o')
        m.connect('dataset_followers', '/dataset/followers/{id}',
                  action='followers', ckan_icon='users')
        m.connect('dataset_activity', '/dataset/activity/{id}',
                  action='activity', ckan_icon='clock-o')
        m.connect('/dataset/activity/{id}/{offset}', action='activity')
        m.connect('dataset_groups', '/dataset/groups/{id}',
                  action='groups', ckan_icon='users')
        m.connect('dataset_resources', '/dataset/resources/{id}',
                  action='resources', ckan_icon='bars')
        m.connect('dataset_read', '/dataset/{id}', action='read',
                  ckan_icon='sitemap')
        m.connect('/dataset/{id}/resource/{resource_id}',
                  action='resource_read')
        m.connect('/dataset/{id}/resource_delete/{resource_id}',
                  action='resource_delete')
        m.connect('resource_edit', '/dataset/{id}/resource_edit/{resource_id}',
                  action='resource_edit', ckan_icon='pencil-square-o')
        m.connect('/dataset/{id}/resource/{resource_id}/download',
                  action='resource_download')
        m.connect('/dataset/{id}/resource/{resource_id}/download/{filename}',
                  action='resource_download')
        m.connect('/dataset/{id}/resource/{resource_id}/embed',
                  action='resource_embedded_dataviewer')
        m.connect('/dataset/{id}/resource/{resource_id}/viewer',
                  action='resource_embedded_dataviewer', width="960",
                  height="800")
        m.connect('/dataset/{id}/resource/{resource_id}/preview',
                  action='resource_datapreview')
        m.connect('views', '/dataset/{id}/resource/{resource_id}/views',
                  action='resource_views', ckan_icon='bars')
        m.connect('new_view', '/dataset/{id}/resource/{resource_id}/new_view',
                  action='edit_view', ckan_icon='pencil-square-o')
        m.connect('edit_view',
                  '/dataset/{id}/resource/{resource_id}/edit_view/{view_id}',
                  action='edit_view', ckan_icon='pencil-square-o')
        m.connect('resource_view',
                  '/dataset/{id}/resource/{resource_id}/view/{view_id}',
                  action='resource_view')
        m.connect('/dataset/{id}/resource/{resource_id}/view/',
                  action='resource_view')

    # group
    map.redirect('/groups', '/group')
    map.redirect('/groups/{url:.*}', '/group/{url}')

    # These named routes are used for custom group forms which will use the
    # names below based on the group.type ('group' is the default type)
    with SubMapper(map, controller='group') as m:
        m.connect('group_index', '/group', action='index',
                  highlight_actions='index search')
        m.connect('group_list', '/group/list', action='list')
        m.connect('group_new', '/group/new', action='new')
        m.connect('group_action', '/group/{action}/{id}',
                  requirements=dict(action='|'.join([
                      'edit',
                      'delete',
                      'member_new',
                      'member_delete',
                      'history',
                      'followers',
                      'follow',
                      'unfollow',
                      'admins',
                      'activity',
                  ])))
        m.connect('group_about', '/group/about/{id}', action='about',
                  ckan_icon='info-circle'),
        m.connect('group_edit', '/group/edit/{id}', action='edit',
                  ckan_icon='pencil-square-o')
        m.connect('group_members', '/group/members/{id}', action='members',
                  ckan_icon='users'),
        m.connect('group_activity', '/group/activity/{id}/{offset}',
                  action='activity', ckan_icon='clock-o'),
        m.connect('group_read', '/group/{id}', action='read',
                  ckan_icon='sitemap')

    # organizations these basically end up being the same as groups
    with SubMapper(map, controller='organization') as m:
        m.connect('organizations_index', '/organization', action='index')
        m.connect('/organization/list', action='list')
        m.connect('/organization/new', action='new')
        m.connect('/organization/{action}/{id}',
                  requirements=dict(action='|'.join([
                      'delete',
                      'admins',
                      'member_new',
                      'member_delete',
                      'history'
                  ])))
        m.connect('organization_activity', '/organization/activity/{id}/{offset}',
                  action='activity', ckan_icon='clock-o')
        m.connect('organization_read', '/organization/{id}', action='read')
        m.connect('organization_about', '/organization/about/{id}',
                  action='about', ckan_icon='info-circle')
        m.connect('organization_read', '/organization/{id}', action='read',
                  ckan_icon='sitemap')
        m.connect('organization_edit', '/organization/edit/{id}',
                  action='edit', ckan_icon='pencil-square-o')
        m.connect('organization_members', '/organization/members/{id}',
                  action='members', ckan_icon='users')
        m.connect('organization_bulk_process',
                  '/organization/bulk_process/{id}',
                  action='bulk_process', ckan_icon='sitemap')
    lib_plugins.register_package_plugins(map)
    lib_plugins.register_group_plugins(map)

    # tags
    map.redirect('/tags', '/tag')
    map.redirect('/tags/{url:.*}', '/tag/{url}')
    map.redirect('/tag/read/{url:.*}', '/tag/{url}',
                 _redirect_code='301 Moved Permanently')
    map.connect('/tag', controller='tag', action='index')
    map.connect('/tag/{id}', controller='tag', action='read')
    # users
    map.redirect('/users/{url:.*}', '/user/{url}')
    map.redirect('/user/', '/user')
    with SubMapper(map, controller='user') as m:
        m.connect('/user/edit', action='edit')
        # Note: openid users have slashes in their ids, so need the wildcard
        # in the route.
        m.connect('user_generate_apikey', '/user/generate_key/{id}', action='generate_apikey')
        m.connect('/user/activity/{id}/{offset}', action='activity')
        m.connect('user_activity_stream', '/user/activity/{id}',
                  action='activity', ckan_icon='clock-o')
        m.connect('user_dashboard', '/dashboard', action='dashboard',
                  ckan_icon='list')
        m.connect('user_dashboard_datasets', '/dashboard/datasets',
                  action='dashboard_datasets', ckan_icon='sitemap')
        m.connect('user_dashboard_groups', '/dashboard/groups',
                  action='dashboard_groups', ckan_icon='users')
        m.connect('user_dashboard_organizations', '/dashboard/organizations',
                  action='dashboard_organizations', ckan_icon='building-o')
        m.connect('/dashboard/{offset}', action='dashboard')
        m.connect('user_follow', '/user/follow/{id}', action='follow')
        m.connect('/user/unfollow/{id}', action='unfollow')
        m.connect('user_followers', '/user/followers/{id:.*}',
                  action='followers', ckan_icon='users')
        m.connect('user_edit', '/user/edit/{id:.*}', action='edit',
                  ckan_icon='cog')
        m.connect('user_delete', '/user/delete/{id}', action='delete')
        m.connect('/user/reset/{id:.*}', action='perform_reset')
        m.connect('register', '/user/register', action='register')
        m.connect('login', '/user/login', action='login')
        m.connect('/user/_logout', action='logout')
        m.connect('/user/logged_in', action='logged_in')
        m.connect('/user/logged_out', action='logged_out')
        m.connect('/user/logged_out_redirect', action='logged_out_page')
        m.connect('/user/reset', action='request_reset')
        m.connect('/user/me', action='me')
        m.connect('/user/set_lang/{lang}', action='set_lang')
        m.connect('user_datasets', '/user/{id:.*}', action='read',
                  ckan_icon='sitemap')
        m.connect('user_index', '/user', action='index')

    with SubMapper(map, controller='revision') as m:
        m.connect('/revision', action='index')
        m.connect('/revision/edit/{id}', action='edit')
        m.connect('/revision/diff/{id}', action='diff')
        m.connect('/revision/list', action='list')
        m.connect('/revision/{id}', action='read')

    # feeds
    with SubMapper(map, controller='feed') as m:
        m.connect('/feeds/group/{id}.atom', action='group')
        m.connect('/feeds/organization/{id}.atom', action='organization')
        m.connect('/feeds/tag/{id}.atom', action='tag')
        m.connect('/feeds/dataset.atom', action='general')
        m.connect('/feeds/custom.atom', action='custom')

    map.connect('ckanadmin_index', '/ckan-admin', controller='admin',
                action='index', ckan_icon='gavel')
    map.connect('ckanadmin_config', '/ckan-admin/config', controller='admin',
                action='config', ckan_icon='check-square-o')
    map.connect('ckanadmin_trash', '/ckan-admin/trash', controller='admin',
                action='trash', ckan_icon='trash-o')
    map.connect('ckanadmin', '/ckan-admin/{action}', controller='admin')

    with SubMapper(map, controller='ckan.controllers.storage:StorageController') as m:
        m.connect('storage_file', '/storage/f/{label:.*}',
                  action='file')

    with SubMapper(map, controller='util') as m:
        m.connect('/i18n/strings_{lang}.js', action='i18n_js_strings')
        m.connect('/util/redirect', action='redirect')
        m.connect('/testing/primer', action='primer')
        m.connect('/testing/markup', action='markup')

    # robots.txt
    map.connect('/(robots.txt)', controller='template', action='view')

    # Mark all unmarked routes added up until now as core routes
    for route in map.matchlist:
        if not hasattr(route, '_ckan_core'):
            route._ckan_core = True

    for plugin in p.PluginImplementations(p.IRoutes):
        map = plugin.after_map(map)

    # Mark all routes added from extensions on the `after_map` extension point
    # as non-core
    for route in map.matchlist:
        if not hasattr(route, '_ckan_core'):
            route._ckan_core = False

    # sometimes we get requests for favicon.ico we should redirect to
    # the real favicon location.
    map.redirect('/favicon.ico', config.get('ckan.favicon'))

    map.redirect('/*(url)/', '/{url}',
                 _redirect_code='301 Moved Permanently')
    map.connect('/*url', controller='template', action='view', ckan_core=True)

    return map
