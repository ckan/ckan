# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class ExampleThemePlugin(plugins.SingletonPlugin):
    '''An example theme plugin.

    '''
    plugins.implements(plugins.IConfigurer)

    def update_config(self, config):

        toolkit.add_template_directory(config, 'templates')
        toolkit.add_resource('assets', 'example_theme')
