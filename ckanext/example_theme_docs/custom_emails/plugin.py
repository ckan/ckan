# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class ExampleCustomEmailsPlugin(plugins.SingletonPlugin):
    '''An example plugin with custom emails.

    '''
    plugins.implements(plugins.IConfigurer)

    def update_config(self, config):

        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        toolkit.add_template_directory(config, 'templates')
