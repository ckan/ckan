# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.types import Schema


class ExampleIConfigurerPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config_schema(self, schema: Schema):

        ignore_missing = toolkit.get_validator('ignore_missing')
        unicode_safe = toolkit.get_validator('unicode_safe')
        is_positive_integer = toolkit.get_validator('is_positive_integer')

        schema.update({
            # This is an existing CKAN core configuration option, we are just
            # making it available to be editable at runtime
            'ckan.datasets_per_page': [ignore_missing, is_positive_integer],

            # This is a custom configuration option
            'ckanext.example_iconfigurer.test_conf': [ignore_missing,
                                                      unicode_safe],
        })

        return schema
