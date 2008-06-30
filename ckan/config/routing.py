"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper

def make_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('error/:action/:id', controller='error')

    # CUSTOM ROUTES HERE

    map.connect('', controller='home', action='index')
    map.connect('api/rest', controller='rest', action='index')
    map.connect('api/rest/:register', controller='rest', action='list',
        conditions=dict(method=['GET']))
    map.connect('api/rest/:register', controller='rest', action='create',
        conditions=dict(method=['POST']))
    map.connect('api/rest/:register/:id', controller='rest', action='show',
        conditions=dict(method=['GET']))
    map.connect('api/rest/:register/:id', controller='rest', action='update',
        conditions=dict(method=['PUT']))
    map.connect('api/rest/:register/:id', controller='rest', action='update',
        conditions=dict(method=['POST']))
    map.connect('api/rest/:register/:id', controller='rest', action='delete',
        conditions=dict(method=['DELETE']))

    map.connect(':controller/:action/:id')
    map.connect('*url', controller='template', action='view')

    return map
