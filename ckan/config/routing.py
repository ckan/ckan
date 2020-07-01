# encoding: utf-8
"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at https://routes.readthedocs.io/en/latest/

"""
import re

from routes.mapper import SubMapper, Mapper as _Mapper

import ckan.plugins as p
from ckan.common import config, current_app

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

    map = Mapper(
        directory=config['pylons.paths']['controllers'],
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

    map.connect(
        '*url',
        controller='home',
        action='cors_options',
        conditions=OPTIONS,
        ckan_core=True)

    # Mark all routes added from extensions on the `before_map` extension point
    # as non-core
    for route in map.matchlist:
        if not hasattr(route, '_ckan_core'):
            route._ckan_core = False

    # /api/util ver 1, 2 or none
    with SubMapper(
            map, controller='api', path_prefix='/api{ver:/1|/2|}',
            ver='/1') as m:
        m.connect('/util/dataset/munge_name', action='munge_package_name')
        m.connect(
            '/util/dataset/munge_title_to_name',
            action='munge_title_to_package_name')
        m.connect('/util/tag/munge', action='munge_tag')

    ###########
    ## /END API
    ###########

    map.redirect('/packages', '/dataset')
    map.redirect('/packages/{url:.*}', '/dataset/{url}')
    map.redirect('/package', '/dataset')
    map.redirect('/package/{url:.*}', '/dataset/{url}')

    # users
    map.redirect('/users/{url:.*}', '/user/{url}')

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

    map.redirect('/*(url)/', '/{url}', _redirect_code='301 Moved Permanently')

    return map
