# encoding: utf-8

from six import text_type

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.example_iconfigurer.blueprint as blueprint


class ExampleIConfigurerPlugin(plugins.SingletonPlugin):
    '''
    An example IConfigurer plugin that shows:

    1. How to implement ``toolkit.add_ckan_admin_tab()`` in the
       ``update_config`` method to add a custom config tab in the admin pages.

    2. How to make CKAN configuration options runtime-editable via
       the web frontend or the API

    '''

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config):
        # Add extension templates directory

        toolkit.add_template_directory(config, 'templates')
        # Add a new ckan-admin tabs for our extension
        toolkit.add_ckan_admin_tab(
            config, 'example_iconfigurer.config_one',
            'My First Custom Config Tab'
        )
        toolkit.add_ckan_admin_tab(
            config, 'example_iconfigurer.config_two',
            'My Second Custom Config Tab'
        )

    def update_config_schema(self, schema):

        ignore_missing = toolkit.get_validator('ignore_missing')
        unicode_safe = toolkit.get_validator('unicode_safe')
        is_positive_integer = toolkit.get_validator('is_positive_integer')

        schema.update({
            # This is an existing CKAN core configuration option, we are just
            # making it available to be editable at runtime
            'ckan.datasets_per_page': [ignore_missing, is_positive_integer],

            # This is a custom configuration option
            'ckanext.example_iconfigurer.test_conf': [
                ignore_missing, unicode_safe
            ],
        })

        return schema

    # IBlueprint

    def get_blueprint(self):
        return blueprint.example_iconfigurer
