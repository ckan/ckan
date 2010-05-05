"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper
from formalchemy.ext.pylons import maps # routes generator

def make_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/:action/:id', controller='error')

    # CUSTOM ROUTES HERE
    map.connect('home', '/', controller='home', action='index')
    map.connect('guide', config.get('guide_url', 'http://wiki.okfn.org/ckan/doc/'), _static=True)
    map.connect('license', '/license', controller='home', action='license')
    map.connect('about', '/about', controller='home', action='about')
    map.connect('stats', '/stats', controller='home', action='stats')
    maps.admin_map(map, controller='admin', url='/admin')
    map.connect('/api/search/:register', controller='rest', action='search')
    map.connect('/api/tag_counts', controller='rest', action='tag_counts')
    map.connect('/api', controller='rest', action='index')
    map.connect('/api/rest', controller='rest', action='index')
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

    map.redirect("/packages", "/package")
    map.redirect("/packages/{url:.*}", "/package/{url}")
    map.connect('/package/', controller='package', action='index')
    map.connect('/package/search', controller='package', action='search')
    map.connect('/package/list', controller='package', action='list')
    map.connect('/package/new', controller='package', action='new')
    map.connect('/package/autocomplete', controller='package', action='autocomplete')
    map.connect('/package/:id', controller='package', action='read')
    map.redirect("/groups", "/group")
    map.redirect("/groups/{url:.*}", "/group/{url}")
    map.connect('/group/', controller='group', action='index')
    map.connect('/group/list', controller='group', action='list')
    map.connect('/group/new', controller='group', action='new')
    map.connect('/group/:id', controller='group', action='read')
    map.redirect("/tags", "/tag")
    map.redirect("/tags/{url:.*}", "/tag/{url}")
    map.redirect("/tag/read/{url:.*}", "/tag/{url}", _redirect_code='301 Moved Permanently')
    map.connect('/tag/', controller='tag', action='index')
    map.connect('/tag/autocomplete', controller='tag', action='autocomplete')
    map.connect('/tag/:id', controller='tag', action='read')
    map.redirect("/users/{url:.*}", "/user/{url}")
    map.connect('/user/all', controller='user', action='all')
    map.connect('/user/edit', controller='user', action='edit')
    map.connect('/user/login', controller='user', action='login')
    map.connect('/user/logout', controller='user', action='logout')
    map.connect('/user/apikey', controller='user', action='apikey')
    map.connect('/user/:id', controller='user', action='read')
    map.connect('/:controller/:action/:id')
    map.connect('/:controller/', action='index')
    map.connect('/:controller/:action/', id=None)
    map.connect('/*url', controller='template', action='view')

    return map
