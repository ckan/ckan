"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/

"""
from pylons import config
from routes import Mapper
from ckan.plugins import PluginImplementations, IRoutes


routing_plugins = PluginImplementations(IRoutes)

def make_map():
    """Create, configure and return the routes Mapper"""
    # import controllers here rather than at root level because 
    # pylons config is initialised by this point.
    from ckan.controllers.package import register_pluggable_behaviour as register_package_behaviour
    from ckan.controllers.group   import register_pluggable_behaviour as register_group_behaviour
    
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False
    map.explicit = True

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved.
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    map.connect('*url', controller='home', action='cors_options', conditions=dict(method=['OPTIONS']))

    # CUSTOM ROUTES HERE
    for plugin in routing_plugins:
        map = plugin.before_map(map)

    map.connect('home', '/', controller='home', action='index')
    map.connect('/locale', controller='home', action='locale')
    map.connect('about', '/about', controller='home', action='about')

    # CKAN API versioned.
    register_list = [
            'package',
            'dataset',
            'resource',
            'tag',
            'group',
            'authorizationgroup',
            'revision',
            'licenses',
            'rating',
            'user',
            'activity'
            ]
    register_list_str = '|'.join(register_list)

    map.connect('/api/{ver:1|2|3}', controller='api', action='get_api')

    map.connect('/api/{ver:1|2|3}/search/{register}', controller='api', action='search')
    map.connect('/api/{ver:1|2}/tag_counts', controller='api', action='tag_counts')

    map.connect('/api/{ver:1|2}/rest', controller='api', action='index')

    map.connect('/api/{ver:1|2}/rest/{register}', controller='api', action='list',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET']))
    map.connect('/api/{ver:1|2}/rest/{register}', controller='api', action='create',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['POST']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}', controller='api', action='show',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}', controller='api', action='update',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['PUT']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}', controller='api', action='update',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['POST']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}', controller='api', action='delete',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['DELETE']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}/:subregister',
        controller='api', action='list',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}/:subregister',
        controller='api', action='create',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['POST']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}/:subregister/{id2}',
        controller='api', action='create',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['POST']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}/:subregister/{id2}',
        controller='api', action='show',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}/:subregister/{id2}',
        controller='api', action='update',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['PUT']))
    map.connect('/api/{ver:1|2}/rest/{register}/{id}/:subregister/{id2}',
        controller='api', action='delete',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['DELETE']))
    map.connect('/api/{ver:3}/action/{logic_function}', controller='api', action='action',
                conditions=dict(method=['GET', 'POST']))
    map.connect('/api/{ver:1|2}/qos/throughput/',
        controller='api', action='throughput',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET']))

    # CKAN API unversioned.
    map.connect('/api', controller='api', action='get_api')

    map.connect('/api/search/{register}', controller='api', action='search')
    map.connect('/api/tag_counts', controller='api', action='tag_counts')
    
    map.connect('/api/rest', controller='api', action='index')

    map.connect('/api/action/{logic_function}', controller='api', action='action',
                conditions=dict(method=['GET', 'POST']))
    map.connect('/api/rest/{register}', controller='api', action='list',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET'])
        )
    map.connect('/api/rest/{register}', controller='api', action='create',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['POST']))
    map.connect('/api/rest/{register}/{id}', controller='api', action='show',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET']))
    map.connect('/api/rest/{register}/{id}', controller='api', action='update',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['PUT']))
    map.connect('/api/rest/{register}/{id}', controller='api', action='update',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['POST']))
    map.connect('/api/rest/{register}/{id}', controller='api', action='delete',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['DELETE']))
    map.connect('/api/rest/{register}/{id}/:subregister',
        controller='api', action='list',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET']))
    map.connect('/api/rest/{register}/{id}/:subregister',
        controller='api', action='create',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['POST']))
    map.connect('/api/rest/{register}/{id}/:subregister/{id2}',
        controller='api', action='create',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['POST']))
    map.connect('/api/rest/{register}/{id}/:subregister/{id2}',
        controller='api', action='show',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['GET']))
    map.connect('/api/rest/{register}/{id}/:subregister/{id2}',
        controller='api', action='update',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['PUT']))
    map.connect('/api/rest/{register}/{id}/:subregister/{id2}',
        controller='api', action='delete',
        requirements=dict(register=register_list_str),
        conditions=dict(method=['DELETE']))
    map.connect('/api/qos/throughput/',
        controller='api', action='throughput',
        conditions=dict(method=['GET']))


    map.connect('/api/2/util/user/autocomplete', controller='api',
        action='user_autocomplete')
    map.connect('/api/2/util/is_slug_valid', controller='api', action='is_slug_valid',
                conditions=dict(method=['GET']))
    map.connect('/api/2/util/dataset/autocomplete', controller='api', action='dataset_autocomplete',
                conditions=dict(method=['GET']))
    map.connect('/api/2/util/tag/autocomplete', controller='api', action='tag_autocomplete',
                conditions=dict(method=['GET']))
    map.connect('/api/2/util/resource/format_autocomplete', controller='api', action='format_autocomplete',
                conditions=dict(method=['GET']))

    map.connect('/api/2/util/authorizationgroup/autocomplete', controller='api',
        action='authorizationgroup_autocomplete')

    map.connect('/api/util/markdown', controller='api', action='markdown')
    map.connect('/api/util/dataset/munge_name', controller='api', action='munge_package_name')
    map.connect('/api/util/dataset/munge_title_to_name', controller='api', action='munge_title_to_package_name')
    map.connect('/api/util/tag/munge', controller='api', action='munge_tag')
    map.connect('/api/util/status', controller='api', action='status')

    ###########
    ## /END API
    ###########
    
    map.redirect("/packages", "/dataset")
    map.redirect("/packages/{url:.*}", "/dataset/{url}")
    map.redirect("/package", "/dataset")
    map.redirect("/package/{url:.*}", "/dataset/{url}")
    map.connect('/dataset', controller='package', action='search')

    ##to get back formalchemy uncomment these lines
    ##map.connect('/package/new', controller='package_formalchemy', action='new')
    ##map.connect('/package/edit/{id}', controller='package_formalchemy', action='edit')

    map.connect('/dataset/{action}', controller='package',
        requirements=dict(action='|'.join([
            'list',
            'new',
            'autocomplete',
            'search'
            ]))
        )

    map.connect('/dataset', controller='package', action='index')
    map.connect('/dataset/{action}/{id}/{revision}', controller='package', action='read_ajax',
        requirements=dict(action='|'.join([
        'read',
        'edit',
        'authz',
        'history',
        ]))
    )
    map.connect('/dataset/{action}/{id}', controller='package',
        requirements=dict(action='|'.join([
        'edit',
        'authz',
        'history',
        'read_ajax',
        'history_ajax',
        ]))
        )
    map.connect('/dataset/{id}', controller='package', action='read')
    map.connect('/dataset/{id}/resource/{resource_id}', 
        controller='package', action="resource_read"
    )

    # group
    map.redirect("/groups", "/group")
    map.redirect("/groups/{url:.*}", "/group/{url}")

    ##to get back formalchemy uncomment these lines
    ##map.connect('/group/new', controller='group_formalchemy', action='new')
    ##map.connect('/group/edit/{id}', controller='group_formalchemy', action='edit')

    # These named routes are used for custom group forms which will use the 
    # names below based on the group.type (dataset_group is the default type)
    map.connect('group_index', '/group', controller='group', action='index')
    map.connect('group_list', '/group/list', controller='group', action='list')
    map.connect('group_new',  '/group/new', controller='group', action='new')    
    map.connect('group_action', '/group/{action}/{id}', controller='group',
        requirements=dict(action='|'.join([
        'edit',
        'authz',
        'history'
        ]))
        )
    map.connect('group_read', '/group/{id}', controller='group', action='read')


    register_package_behaviour(map)
    register_group_behaviour(map)    
    
    # authz group
    map.redirect("/authorizationgroups", "/authorizationgroup")
    map.redirect("/authorizationgroups/{url:.*}", "/authorizationgroup/{url}")
    map.connect('/authorizationgroup', controller='authorization_group', action='index')
    map.connect('/authorizationgroup/list', controller='authorization_group', action='list')
    map.connect('/authorizationgroup/new', controller='authorization_group', action='new')
    map.connect('/authorizationgroup/edit/{id}', controller='authorization_group', action='edit')
    map.connect('/authorizationgroup/authz/{id}', controller='authorization_group', action='authz')
    map.connect('/authorizationgroup/{id}', controller='authorization_group', action='read')
    # tags
    map.redirect("/tags", "/tag")
    map.redirect("/tags/{url:.*}", "/tag/{url}")
    map.redirect("/tag/read/{url:.*}", "/tag/{url}", _redirect_code='301 Moved Permanently')
    map.connect('/tag', controller='tag', action='index')
    map.connect('/tag/{id}', controller='tag', action='read')
    # users
    map.redirect("/users/{url:.*}", "/user/{url}")
    map.redirect("/user/", "/user")
    map.connect('/user/edit', controller='user', action='edit')
    # Note: openid users have slashes in their ids, so need the wildcard
    # in the route.
    map.connect('/user/edit/{id:.*}', controller='user', action='edit')
    map.connect('/user/reset/{id:.*}', controller='user', action='perform_reset')
    map.connect('/user/register', controller='user', action='register')
    map.connect('/user/login', controller='user', action='login')
    map.connect('/user/logged_in', controller='user', action='logged_in')
    map.connect('/user/logged_out', controller='user', action='logged_out')
    map.connect('/user/reset', controller='user', action='request_reset')
    map.connect('/user/me', controller='user', action='me')
    map.connect('/user/{id:.*}', controller='user', action='read')
    map.connect('/user', controller='user', action='index')

    map.connect('/revision', controller='revision', action='index')
    map.connect('/revision/edit/{id}', controller='revision', action='edit')
    map.connect('/revision/diff/{id}', controller='revision', action='diff')
    map.connect('/revision/list', controller='revision', action='list')
    map.connect('/revision/{id}', controller='revision', action='read')

    map.connect('ckanadmin_index', '/ckan-admin', controller='admin', action='index')
    map.connect('ckanadmin', '/ckan-admin/{action}', controller='admin')
    
    # Storage routes
    map.connect('storage_api', "/api/storage", 
                controller='ckan.controllers.storage:StorageAPIController', 
                action='index')
    map.connect('storage_api_set_metadata', '/api/storage/metadata/{label:.*}', 
                controller='ckan.controllers.storage:StorageAPIController', 
                action='set_metadata',
                conditions={'method': ['PUT','POST']})
    map.connect('storage_api_get_metadata', '/api/storage/metadata/{label:.*}', 
                controller='ckan.controllers.storage:StorageAPIController', 
                action='get_metadata',
                conditions={'method': ['GET']})
    map.connect('storage_api_auth_request',
                '/api/storage/auth/request/{label:.*}',
                controller='ckan.controllers.storage:StorageAPIController',
                action='auth_request')
    map.connect('storage_api_auth_form',
                '/api/storage/auth/form/{label:.*}',
                controller='ckan.controllers.storage:StorageAPIController',
                action='auth_form')
    map.connect('storage_upload', '/storage/upload',
                controller='ckan.controllers.storage:StorageController',
                action='upload')
    map.connect('storage_upload_handle', '/storage/upload_handle',
                controller='ckan.controllers.storage:StorageController',
                action='upload_handle')
    map.connect('storage_upload_success', '/storage/upload/success',
                controller='ckan.controllers.storage:StorageController',
                action='success')
    map.connect('storage_upload_success_empty', '/storage/upload/success_empty',
                controller='ckan.controllers.storage:StorageController',
                action='success_empty')
    map.connect('storage_file', '/storage/f/{label:.*}',
                controller='ckan.controllers.storage:StorageController',
                action='file')
    
    
    for plugin in routing_plugins:
        map = plugin.after_map(map)
    
    
    map.redirect('/*(url)/', '/{url}',
                 _redirect_code='301 Moved Permanently')
    map.connect('/*url', controller='template', action='view')

    return map
