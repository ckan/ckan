"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper
from formalchemy.ext.pylons import maps # routes generator
from ckan.plugins import ExtensionPoint, IRoutesExtension

routing_plugins = ExtensionPoint(IRoutesExtension)

def make_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved.
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE
    for plugin in routing_plugins:
        map = plugin.before_map(map)
        
    map.connect('home', '/', controller='home', action='index')
    map.connect('guide', config.get('guide_url', 'http://wiki.okfn.org/ckan/doc/'), _static=True)
    map.connect('license', '/license', controller='home', action='license')
    map.connect('about', '/about', controller='home', action='about')
    map.connect('stats', '/stats', controller='home', action='stats')
    # TODO get admin controller working again #829
    #maps.admin_map(map, controller='admin', url='/admin')
    # CKAN API.
    map.connect('/api', controller='rest', action='get_api')
    map.connect('/api/form/package/create', controller='form', action='package_create')
    map.connect('/api/form/package/edit/:id', controller='form', action='package_edit')
    map.connect('/api/form/harvestsource/create', controller='form', action='harvest_source_create')
    map.connect('/api/form/harvestsource/edit/:id', controller='form', action='harvest_source_edit')

    map.connect('/api/search/:register', controller='rest', action='search')
    map.connect('/api/tag_counts', controller='rest', action='tag_counts')
    
    map.connect('/api/rest', controller='rest', action='index')
    
    map.connect('/api/rest/package', controller='apiv1/package', action='list',
                conditions=dict(method=['GET']))
    map.connect('/api/rest/package', controller='apiv1/package', action='create',
                conditions=dict(method=['POST']))
    map.connect('/api/rest/package/:id', controller='apiv1/package', action='show',
                conditions=dict(method=['GET']))
    map.connect('/api/rest/package/:id', controller='apiv1/package', action='update',
                conditions=dict(method=['POST']))
    map.connect('/api/rest/package/:id', controller='apiv1/package', action='update',
                conditions=dict(method=['PUT']))
    map.connect('/api/rest/package/:id', controller='apiv1/package', action='delete',
                conditions=dict(method=['DELETE']))

    map.connect('/api/rest/package', controller='apiv1/package', action='list',
                conditions=dict(method=['GET']))
    map.connect('/api/rest/package', controller='apiv1/package', action='create',
                conditions=dict(method=['POST']))
    map.connect('/api/rest/package/:id', controller='apiv1/package', action='show',
                conditions=dict(method=['GET']))
    map.connect('/api/rest/package/:id', controller='apiv1/package', action='update',
                conditions=dict(method=['POST']))
    map.connect('/api/rest/package/:id', controller='apiv1/package', action='update',
                conditions=dict(method=['PUT']))
    map.connect('/api/rest/package/:id', controller='apiv1/package', action='delete',
                conditions=dict(method=['DELETE']))

    map.connect('/api/rest/:register', controller='rest', action='list',
        conditions=dict(method=['GET']))
    map.connect('/api/rest/:register', controller='rest', action='create',
        conditions=dict(method=['POST']))
    map.connect('/api/rest/:register/:id', controller='rest', action='show',
        conditions=dict(method=['GET']))
    map.connect('/api/rest/:register/:id', controller='rest', action='update',
        conditions=dict(method=['PUT']))
    map.connect('/api/rest/:register/:id', controller='rest', action='update',
        conditions=dict(method=['POST']))
    map.connect('/api/rest/:register/:id', controller='rest', action='delete',
        conditions=dict(method=['DELETE']))
    map.connect('/api/rest/:register/:id/:subregister',
        controller='rest', action='list',
        conditions=dict(method=['GET']))
    map.connect('/api/rest/:register/:id/:subregister/:id2',
        controller='rest', action='create',
        conditions=dict(method=['POST']))
    map.connect('/api/rest/:register/:id/:subregister/:id2',
        controller='rest', action='show',
        conditions=dict(method=['GET']))
    map.connect('/api/rest/:register/:id/:subregister/:id2',
        controller='rest', action='update',
        conditions=dict(method=['PUT']))
    map.connect('/api/rest/:register/:id/:subregister/:id2',
        controller='rest', action='delete',
        conditions=dict(method=['DELETE']))
    map.connect('/api/qos/throughput/',
        controller='rest', action='throughput',
        conditions=dict(method=['GET']))

    # CKAN API v1.
    map.connect('/api/1', controller='rest', action='get_api')
    map.connect('/api/1/form/package/create', controller='form', action='package_create')
    map.connect('/api/1/form/package/edit/:id', controller='form', action='package_edit')
    map.connect('/api/1/form/harvestsource/create', controller='form', action='harvest_source_create')
    map.connect('/api/1/form/harvestsource/edit/:id', controller='form', action='harvest_source_edit')

    map.connect('/api/1/search/:register', controller='rest', action='search')
    map.connect('/api/1/tag_counts', controller='rest', action='tag_counts')

    map.connect('/api/1/rest', controller='rest', action='index')

    map.connect('/api/1/rest/package', controller='apiv1/package', action='list',
                conditions=dict(method=['GET']))
    map.connect('/api/1/rest/package', controller='apiv1/package', action='create',
                conditions=dict(method=['POST']))
    map.connect('/api/1/rest/package/:id', controller='apiv1/package', action='show',
                conditions=dict(method=['GET']))
    map.connect('/api/1/rest/package/:id', controller='apiv1/package', action='update',
                conditions=dict(method=['POST']))
    map.connect('/api/1/rest/package/:id', controller='apiv1/package', action='update',
                conditions=dict(method=['PUT']))
    map.connect('/api/1/rest/package/:id', controller='apiv1/package', action='delete',
                conditions=dict(method=['DELETE']))

    map.connect('/api/1/rest/:register', controller='rest', action='list',
        conditions=dict(method=['GET']))
    map.connect('/api/1/rest/:register', controller='rest', action='create',
        conditions=dict(method=['POST']))
    map.connect('/api/1/rest/:register/:id', controller='rest', action='show',
        conditions=dict(method=['GET']))
    map.connect('/api/1/rest/:register/:id', controller='rest', action='update',
        conditions=dict(method=['PUT']))
    map.connect('/api/1/rest/:register/:id', controller='rest', action='update',
        conditions=dict(method=['POST']))
    map.connect('/api/1/rest/:register/:id', controller='rest', action='delete',
        conditions=dict(method=['DELETE']))
    map.connect('/api/1/rest/:register/:id/:subregister',
        controller='rest', action='list',
        conditions=dict(method=['GET']))
    map.connect('/api/1/rest/:register/:id/:subregister/:id2',
        controller='rest', action='create',
        conditions=dict(method=['POST']))
    map.connect('/api/1/rest/:register/:id/:subregister/:id2',
        controller='rest', action='show',
        conditions=dict(method=['GET']))
    map.connect('/api/1/rest/:register/:id/:subregister/:id2',
        controller='rest', action='update',
        conditions=dict(method=['PUT']))
    map.connect('/api/1/rest/:register/:id/:subregister/:id2',
        controller='rest', action='delete',
        conditions=dict(method=['DELETE']))
    map.connect('/api/1/qos/throughput/',
        controller='rest', action='throughput',
        conditions=dict(method=['GET']))

    # CKAN API v2.
    map.connect('/api/2', controller='rest2', action='get_api')
    map.connect('/api/2/form/package/create', controller='form2', action='package_create')
    map.connect('/api/2/form/package/edit/:id', controller='form2', action='package_edit')
    map.connect('/api/2/form/harvestsource/create', controller='form', action='harvest_source_create')
    map.connect('/api/2/form/harvestsource/edit/:id', controller='form', action='harvest_source_edit')

    map.connect('/api/2/search/:register', controller='rest2', action='search')
    map.connect('/api/2/tag_counts', controller='rest2', action='tag_counts')

    map.connect('/api/2/rest', controller='rest2', action='index')

    map.connect('/api/2/rest/package', controller='apiv2/package', action='list',
                conditions=dict(method=['GET']))
    map.connect('/api/2/util/package/create_slug', controller='apiv2/package', action='create_slug',
                conditions=dict(method=['GET']))
    map.connect('/api/2/util/tag/autocomplete', controller='apiv2/package', action='autocomplete',
                conditions=dict(method=['GET']))
    map.connect('/api/2/rest/package', controller='apiv2/package', action='create',
                conditions=dict(method=['POST']))
    map.connect('/api/2/rest/package/:id', controller='apiv2/package', action='show',
                conditions=dict(method=['GET']))
    map.connect('/api/2/rest/package/:id', controller='apiv2/package', action='update',
                conditions=dict(method=['POST']))
    map.connect('/api/2/rest/package/:id', controller='apiv2/package', action='update',
                conditions=dict(method=['PUT']))
    map.connect('/api/2/rest/package/:id', controller='apiv2/package', action='delete',
                conditions=dict(method=['DELETE']))

    map.connect('/api/2/rest/:register', controller='rest2', action='list',
        conditions=dict(method=['GET']))
    map.connect('/api/2/rest/:register', controller='rest2', action='create',
        conditions=dict(method=['POST']))
    map.connect('/api/2/rest/:register/:id', controller='rest2', action='show',
        conditions=dict(method=['GET']))
    map.connect('/api/2/rest/:register/:id', controller='rest2', action='update',
        conditions=dict(method=['PUT']))
    map.connect('/api/2/rest/:register/:id', controller='rest2', action='update',
        conditions=dict(method=['POST']))
    map.connect('/api/2/rest/:register/:id', controller='rest2', action='delete',
        conditions=dict(method=['DELETE']))
    map.connect('/api/2/rest/:register/:id/:subregister',
        controller='rest2', action='list',
        conditions=dict(method=['GET']))
    map.connect('/api/2/rest/:register/:id/:subregister/:id2',
        controller='rest2', action='create',
        conditions=dict(method=['POST']))
    map.connect('/api/2/rest/:register/:id/:subregister/:id2',
        controller='rest2', action='show',
        conditions=dict(method=['GET']))
    map.connect('/api/2/rest/:register/:id/:subregister/:id2',
        controller='rest2', action='update',
        conditions=dict(method=['PUT']))
    map.connect('/api/2/rest/:register/:id/:subregister/:id2',
        controller='rest2', action='delete',
        conditions=dict(method=['DELETE']))
    map.connect('/api/2/qos/throughput/',
        controller='rest', action='throughput',
        conditions=dict(method=['GET']))

    map.redirect("/packages", "/package")
    map.redirect("/packages/{url:.*}", "/package/{url}")
    map.connect('/package', controller='package', action='search')
    map.connect('/package/', controller='package', action='search')
    map.connect('/package/search', controller='package', action='search')
    map.connect('/package/list', controller='package', action='search')
    map.connect('/package/new', controller='package', action='new')
    map.connect('/package/new_title_to_slug', controller='package', action='new_title_to_slug')
    map.connect('/package/autocomplete', controller='package', action='autocomplete')
    map.connect('/package/:id', controller='package', action='read')
    map.redirect("/groups", "/group")
    map.redirect("/groups/{url:.*}", "/group/{url}")
    map.connect('/group/', controller='group', action='index')
    map.connect('/group/list', controller='group', action='list')
    map.connect('/group/new', controller='group', action='new')
    map.connect('/group/:id', controller='group', action='read')
    map.redirect("/authorizationgroups", "/authorizationgroup")
    map.redirect("/authorizationgroups/{url:.*}", "/authorizationgroup/{url}")
    map.connect('/authorizationgroup', controller='authorization_group', action='index')
    map.connect('/authorizationgroup/list', controller='authorization_group', action='list')
    map.connect('/authorizationgroup/new', controller='authorization_group', action='new')
    map.connect('/authorizationgroup/edit/:id', controller='authorization_group', action='edit')
    map.connect('/authorizationgroup/authz/:id', controller='authorization_group', action='authz')
    map.connect('/authorizationgroup/:id', controller='authorization_group', action='read')
    map.redirect("/tags", "/tag")
    map.redirect("/tags/{url:.*}", "/tag/{url}")
    map.redirect("/tag/read/{url:.*}", "/tag/{url}", _redirect_code='301 Moved Permanently')
    map.connect('/tag/', controller='tag', action='index')
    map.connect('/tag/:id', controller='tag', action='read')
    map.redirect("/users/{url:.*}", "/user/{url}")
    map.connect('/user/all', controller='user', action='all')
    map.connect('/user/edit', controller='user', action='edit')
    map.connect('/user/login', controller='user', action='login')
    map.connect('/user/openid', controller='user', action='openid')
    map.connect('/user/logout', controller='user', action='logout')
    map.connect('/user/apikey', controller='user', action='apikey')
    map.connect('/user/:id', controller='user', action='read')
    map.connect('/{controller}', action='index')
    map.connect('/:controller/{action}')
    map.connect('/{controller}/{action}/{id}')
    
    for plugin in routing_plugins:
        map = plugin.after_map(map)
    
    map.redirect('/*(url)/', '/{url}',
                 _redirect_code='301 Moved Permanently')
    map.connect('/*url', controller='template', action='view')

    return map
