"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/

"""
import re

from pylons import config
from routes.mapper import SubMapper, Mapper as _Mapper

from ckan.plugins import PluginImplementations, IRoutes

named_routes = {}

routing_plugins = PluginImplementations(IRoutes)


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
            e.g. 'group', 'time'
        :type ckan_icon: string
        :param highlight_actions: space-separated list of controller actions
            that should be treated as the same as this named route for menu
            highlighting purposes, e.g. 'index search'
        :type highlight_actions: string

        '''
        ckan_icon = kw.pop('ckan_icon', None)
        highlight_actions = kw.pop('highlight_actions', kw.get('action', ''))
        out = _Mapper.connect(self, *args, **kw)
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

    from ckan.lib.plugins import register_package_plugins
    from ckan.lib.plugins import register_group_plugins

    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False
    map.explicit = True

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved.
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    map.connect('*url', controller='home', action='cors_options',
                conditions=OPTIONS)

    # CUSTOM ROUTES HERE
    for plugin in routing_plugins:
        map = plugin.before_map(map)

    map.connect('home', '/', controller='home', action='index')
    map.connect('about', '/about', controller='home', action='about')

    # CKAN API versioned.
    register_list = [
        'package',
        'dataset',
        'resource',
        'tag',
        'group',
        'related',
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
        m.connect('', action='get_api')
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

    with SubMapper(map, controller='related') as m:
        m.connect('related_new', '/dataset/{id}/related/new', action='new')
        m.connect('related_edit', '/dataset/{id}/related/edit/{related_id}',
                  action='edit')
        m.connect('related_delete', '/dataset/{id}/related/delete/{related_id}',
                  action='delete')
        m.connect('related_list', '/dataset/{id}/related', action='list',
                  ckan_icon='picture')
        m.connect('related_read', '/related/{id}', action='read')
        m.connect('related_dashboard', '/related', action='dashboard')

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
                      'edit',
                      'new_metadata',
                      'new_resource',
                      'history',
                      'read_ajax',
                      'history_ajax',
                      'follow',
                      'activity',
                      'unfollow',
                      'delete',
                      'api_data',
                  ])))
        m.connect('dataset_followers', '/dataset/followers/{id}',
                  action='followers', ckan_icon='group')
        m.connect('dataset_activity', '/dataset/activity/{id}',
                  action='activity', ckan_icon='time')
        m.connect('/dataset/activity/{id}/{offset}', action='activity')
        m.connect('/dataset/{id}.{format}', action='read')
        m.connect('dataset_read', '/dataset/{id}', action='read',
                  ckan_icon='sitemap')
        m.connect('/dataset/{id}/resource/{resource_id}',
                  action='resource_read')
        m.connect('/dataset/{id}/resource_delete/{resource_id}',
                  action='resource_delete')
        m.connect('/dataset/{id}/resource_edit/{resource_id}',
                  action='resource_edit')
        m.connect('/dataset/{id}/resource/{resource_id}/download',
                  action='resource_download')
        m.connect('/dataset/{id}/resource/{resource_id}/embed',
                  action='resource_embedded_dataviewer')
        m.connect('/dataset/{id}/resource/{resource_id}/viewer',
                  action='resource_embedded_dataviewer', width="960",
                  height="800")
        m.connect('/dataset/{id}/resource/{resource_id}/preview',
                  action='resource_datapreview')

    # group
    map.redirect('/groups', '/group')
    map.redirect('/groups/{url:.*}', '/group/{url}')

    ##to get back formalchemy uncomment these lines
    ##map.connect('/group/new', controller='group_formalchemy', action='new')
    ##map.connect('/group/edit/{id}', controller='group_formalchemy', action='edit')

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
                  ckan_icon='info-sign'),
        m.connect('group_edit', '/group/edit/{id}', action='edit',
                  ckan_icon='edit')
        m.connect('group_members', '/group/members/{id}', action='members',
                  ckan_icon='group'),
        m.connect('group_activity', '/group/activity/{id}/{offset}',
                  action='activity', ckan_icon='time'),
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
        m.connect('organization_activity', '/organization/activity/{id}',
                  action='activity', ckan_icon='time')
        m.connect('organization_read', '/organization/{id}', action='read')
        m.connect('organization_about', '/organization/about/{id}',
                  action='about', ckan_icon='info-sign')
        m.connect('organization_read', '/organization/{id}', action='read',
                  ckan_icon='sitemap')
        m.connect('organization_edit', '/organization/edit/{id}',
                  action='edit', ckan_icon='edit')
        m.connect('organization_members', '/organization/members/{id}',
                  action='members', ckan_icon='group')
        m.connect('organization_bulk_process',
                  '/organization/bulk_process/{id}',
                  action='bulk_process', ckan_icon='sitemap')
    register_package_plugins(map)
    register_group_plugins(map)

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
        m.connect('/user/activity/{id}/{offset}', action='activity')
        m.connect('user_activity_stream', '/user/activity/{id}',
                  action='activity', ckan_icon='time')
        m.connect('user_dashboard', '/dashboard', action='dashboard',
                  ckan_icon='list')
        m.connect('user_dashboard_datasets', '/dashboard/datasets',
                  action='dashboard_datasets', ckan_icon='sitemap')
        m.connect('user_dashboard_groups', '/dashboard/groups',
                  action='dashboard_groups', ckan_icon='group')
        m.connect('user_dashboard_organizations', '/dashboard/organizations',
                  action='dashboard_organizations', ckan_icon='building')
        m.connect('/dashboard/{offset}', action='dashboard')
        m.connect('user_follow', '/user/follow/{id}', action='follow')
        m.connect('/user/unfollow/{id}', action='unfollow')
        m.connect('user_followers', '/user/followers/{id:.*}',
                  action='followers', ckan_icon='group')
        m.connect('user_edit', '/user/edit/{id:.*}', action='edit',
                  ckan_icon='cog')
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
        m.connect('/feeds/tag/{id}.atom', action='tag')
        m.connect('/feeds/dataset.atom', action='general')
        m.connect('/feeds/custom.atom', action='custom')

    map.connect('ckanadmin_index', '/ckan-admin', controller='admin',
                action='index', ckan_icon='legal')
    map.connect('ckanadmin_config', '/ckan-admin/config', controller='admin',
                action='config', ckan_icon='check')
    map.connect('ckanadmin', '/ckan-admin/{action}', controller='admin')

    # Storage routes
    with SubMapper(map, controller='ckan.controllers.storage:StorageAPIController') as m:
        m.connect('storage_api', '/api/storage', action='index')
        m.connect('storage_api_set_metadata', '/api/storage/metadata/{label:.*}',
                  action='set_metadata', conditions=PUT_POST)
        m.connect('storage_api_get_metadata', '/api/storage/metadata/{label:.*}',
                  action='get_metadata', conditions=GET)
        m.connect('storage_api_auth_request',
                  '/api/storage/auth/request/{label:.*}',
                  action='auth_request')
        m.connect('storage_api_auth_form',
                  '/api/storage/auth/form/{label:.*}',
                  action='auth_form')

    with SubMapper(map, controller='ckan.controllers.storage:StorageController') as m:
        m.connect('storage_upload', '/storage/upload',
                  action='upload')
        m.connect('storage_upload_handle', '/storage/upload_handle',
                  action='upload_handle')
        m.connect('storage_upload_success', '/storage/upload/success',
                  action='success')
        m.connect('storage_upload_success_empty', '/storage/upload/success_empty',
                  action='success_empty')
        m.connect('storage_file', '/storage/f/{label:.*}',
                  action='file')

    with SubMapper(map, controller='util') as m:
        m.connect('/i18n/strings_{lang}.js', action='i18n_js_strings')
        m.connect('/util/redirect', action='redirect')
        m.connect('/testing/primer', action='primer')
        m.connect('/testing/markup', action='markup')

    for plugin in routing_plugins:
        map = plugin.after_map(map)

    # sometimes we get requests for favicon.ico we should redirect to
    # the real favicon location.
    map.redirect('/favicon.ico', config.get('ckan.favicon'))

    map.redirect('/*(url)/', '/{url}',
                 _redirect_code='301 Moved Permanently')
    map.connect('/*url', controller='template', action='view')

    return map
