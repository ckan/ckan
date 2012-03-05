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


    # Helpers to reduce code clutter
    GET = dict(method=['GET'])
    PUT = dict(method=['PUT'])
    POST = dict(method=['POST'])
    DELETE = dict(method=['DELETE'])
    GET_POST = dict(method=['GET', 'POST'])
    PUT_POST = dict(method=['PUT','POST'])
    OPTIONS = dict(method=['OPTIONS'])

    from lib.plugins import register_package_plugins
    from lib.plugins import register_group_plugins

    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False
    map.explicit = True

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved.
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    map.connect('*url', controller='home', action='cors_options', conditions=OPTIONS)

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
            'authorizationgroup',
            'revision',
            'licenses',
            'rating',
            'user',
            'activity'
            ]
    register_list_str = '|'.join(register_list)

    # /api ver 3 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/3|}', ver='/3') as m:
        m.connect('/action/{logic_function}', action='action',
                  conditions=GET_POST)

    # /api ver 1, 2, 3 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|/3|}', ver='/1') as m:
        m.connect('', action='get_api')
        m.connect('/search/{register}', action='search')

    # /api ver 1, 2 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|}', ver='/1') as m:
        m.connect('/tag_counts', action='tag_counts')
        m.connect('/rest', action='index')
        m.connect('/qos/throughput/', action='throughput', conditions=GET)

    # /api/rest ver 1, 2 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|}', ver='/1',
                   requirements=dict(register=register_list_str)) as m:

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

    # /api/2/util
    with SubMapper(map, controller='api', path_prefix='/api{ver:/2}', ver='/2') as m:
        m.connect('/util/user/autocomplete', action='user_autocomplete')
        m.connect('/util/is_slug_valid', action='is_slug_valid',
                  conditions=GET)
        m.connect('/util/dataset/autocomplete', action='dataset_autocomplete',
                  conditions=GET)
        m.connect('/util/tag/autocomplete', action='tag_autocomplete',
                  conditions=GET)
        m.connect('/util/resource/format_autocomplete',
                  action='format_autocomplete', conditions=GET)
        m.connect('/util/authorizationgroup/autocomplete',
                  action='authorizationgroup_autocomplete')
        m.connect('/util/group/autocomplete', action='group_autocomplete')

    # /api/util
    with SubMapper(map, controller='api', path_prefix='/api') as m:
        m.connect('/util/markdown', action='markdown')
        m.connect('/util/dataset/munge_name', action='munge_package_name')
        m.connect('/util/dataset/munge_title_to_name',
                  action='munge_title_to_package_name')
        m.connect('/util/tag/munge', action='munge_tag')
        m.connect('/util/status', action='status')

    ## Webstore
    if config.get('ckan.datastore.enabled', False):
        map.connect('datastore_read', '/api/data/{id}{url:(/.*)?}',
            controller='datastore', action='read', url='',
            conditions={'method': ['GET']}
            )
        map.connect('datastore_write', '/api/data/{id}{url:(/.*)?}',
            controller='datastore', action='write', url='',
            conditions={'method': ['PUT','POST', 'DELETE']}
            )


    ###########
    ## /END API
    ###########

    map.redirect('/packages', '/dataset')
    map.redirect('/packages/{url:.*}', '/dataset/{url}')
    map.redirect('/package', '/dataset')
    map.redirect('/package/{url:.*}', '/dataset/{url}')

    ##to get back formalchemy uncomment these lines
    ##map.connect('/package/new', controller='package_formalchemy', action='new')
    ##map.connect('/package/edit/{id}', controller='package_formalchemy', action='edit')

    with SubMapper(map, controller='package') as m:
        m.connect('/dataset', action='search')
        m.connect('/dataset/{action}',
          requirements=dict(action='|'.join([
              'list',
              'new',
              'autocomplete',
              'search'
              ]))
          )

        m.connect('/dataset/{action}/{id}/{revision}', action='read_ajax',
          requirements=dict(action='|'.join([
          'read',
          'edit',
          'authz',
          'history',
          ]))
        )
        m.connect('/dataset/{action}/{id}',
          requirements=dict(action='|'.join([
          'edit',
          'authz',
          'history',
          'read_ajax',
          'history_ajax',
          ]))
          )
        m.connect('/dataset/{id}', action='read')
        m.connect('/dataset/{id}/resource/{resource_id}', action='resource_read')

    # group
    map.redirect('/groups', '/group')
    map.redirect('/groups/{url:.*}', '/group/{url}')

    ##to get back formalchemy uncomment these lines
    ##map.connect('/group/new', controller='group_formalchemy', action='new')
    ##map.connect('/group/edit/{id}', controller='group_formalchemy', action='edit')

    # These named routes are used for custom group forms which will use the
    # names below based on the group.type (dataset_group is the default type)
    with SubMapper(map, controller='group') as m:
        m.connect('group_index', '/group', action='index')
        m.connect('group_list', '/group/list', action='list')
        m.connect('group_new',  '/group/new', action='new')
        m.connect('group_action', '/group/{action}/{id}',
          requirements=dict(action='|'.join([
          'edit',
          'authz',
          'history'
          ]))
          )
        m.connect('group_read', '/group/{id}', action='read')

    register_package_plugins(map)
    register_group_plugins(map)


    # authz group
    map.redirect('/authorizationgroups', '/authorizationgroup')
    map.redirect('/authorizationgroups/{url:.*}', '/authorizationgroup/{url}')
    with SubMapper(map, controller='authorization_group') as m:
        m.connect('/authorizationgroup', action='index')
        m.connect('/authorizationgroup/list', action='list')
        m.connect('/authorizationgroup/new', action='new')
        m.connect('/authorizationgroup/edit/{id}', action='edit')
        m.connect('/authorizationgroup/authz/{id}', action='authz')
        m.connect('/authorizationgroup/{id}', action='read')

    # tags
    map.redirect('/tags', '/tag')
    map.redirect('/tags/{url:.*}', '/tag/{url}')
    map.redirect('/tag/read/{url:.*}', '/tag/{url}', _redirect_code='301 Moved Permanently')
    map.connect('/tag', controller='tag', action='index')
    map.connect('/tag/{id}', controller='tag', action='read')
    # users
    map.redirect('/users/{url:.*}', '/user/{url}')
    map.redirect('/user/', '/user')
    with SubMapper(map, controller='user') as m:
        m.connect('/user/edit', action='edit')
        # Note: openid users have slashes in their ids, so need the wildcard
        # in the route.
        m.connect('/user/edit/{id:.*}', action='edit')
        m.connect('/user/reset/{id:.*}', action='perform_reset')
        m.connect('/user/register', action='register')
        m.connect('/user/login', action='login')
        m.connect('/user/logged_in', action='logged_in')
        m.connect('/user/logged_out', action='logged_out')
        m.connect('/user/reset', action='request_reset')
        m.connect('/user/me', action='me')
        m.connect('/user/{id:.*}', action='read')
        m.connect('/user', action='index')

    with SubMapper(map, controller='revision') as m:
        m.connect('/revision', action='index')
        m.connect('/revision/edit/{id}', action='edit')
        m.connect('/revision/diff/{id}', action='diff')
        m.connect('/revision/list', action='list')
        m.connect('/revision/{id}', action='read')

    map.connect('ckanadmin_index', '/ckan-admin', controller='admin', action='index')
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


    for plugin in routing_plugins:
        map = plugin.after_map(map)


    map.redirect('/*(url)/', '/{url}',
                 _redirect_code='301 Moved Permanently')
    map.connect('/*url', controller='template', action='view')

    return map

class SubMapper(object):
    # FIXME this is only used due to a bug in routes 1.11
    # hopefully we can use map.submapper(...) in version 1.12
    """Partial mapper for use with_options"""
    def __init__(self, obj, **kwargs):
        self.kwargs = kwargs
        self.obj = obj

    def connect(self, *args, **kwargs):
        newkargs = {}
        newargs = args
        for key in self.kwargs:
            if key == 'path_prefix':
                if len(args) > 1:
                    newargs = (args[0], self.kwargs[key] + args[1])
                else:
                    newargs = (self.kwargs[key] + args[0],)
            elif key in kwargs:
                newkargs[key] = self.kwargs[key] + kwargs[key]
            else:
                newkargs[key] = self.kwargs[key]
        for key in kwargs:
            if key not in self.kwargs:
                newkargs[key] = kwargs[key]
        return self.obj.connect(*newargs, **newkargs)

    # Provided for those who prefer using the 'with' syntax in Python 2.5+
    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass
