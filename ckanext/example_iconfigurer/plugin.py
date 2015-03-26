from routes.mapper import SubMapper

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class ExampleIConfigurerPlugin(plugins.SingletonPlugin):

    '''
    An example IConfigurer plugin implementing toolkit.add_ckan_admin_tab() in
    the update_config method.
    '''

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes, inherit=True)

    def update_config(self, config):
        # Add extension templates directory
        toolkit.add_template_directory(config, 'templates')
        # Add a new ckan-admin tabs for our extension
        toolkit.add_ckan_admin_tab(config, 'ckanext_myext_config_one',
                                   'My First Custom Config Tab')
        toolkit.add_ckan_admin_tab(config, 'ckanext_myext_config_two',
                                   'My Second Custom Config Tab')
        toolkit.add_ckan_admin_tab(config, 'ckanext_myext_config_two',
                                   'My Second Custom Config Tab')

    def before_map(self, map):
        controller = 'ckanext.example_iconfigurer.controller:MyExtController'
        with SubMapper(map, controller=controller) as m:
            m.connect('ckanext_myext_config_one',
                      '/ckan-admin/myext_config_one', action='config_one',
                      ckan_icon='picture'),
            m.connect('ckanext_myext_config_two',
                      '/ckan-admin/myext_config_two', action='config_two',
                      ckan_icon='picture'),
        return map
