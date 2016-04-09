from routes.mapper import SubMapper

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk


class ExampleIRoutesPlugin(plugins.SingletonPlugin):

    '''
    An example IRoutes plugin that shows:

    * Adding a route
    * Changing the path of a route
    '''

    plugins.implements(plugins.IRoutes, inherit=True)

    # IRoutes

    def before_map(self, map):
        controller = 'ckanext.example_iroutes.controller:DashboardController'

        # Adding a route
        with SubMapper(map, controller=controller) as m:
            m.connect('main_dash',
                      '/dashboard/main', action='main',
                      ckan_icon='dashboard'),
            m.connect('test1',
                      '/dashboard/main', action='test', testid='1'),

        # Changing the path of a route
        tk._delete_routes_by_name(map, 'test1')

        return map
