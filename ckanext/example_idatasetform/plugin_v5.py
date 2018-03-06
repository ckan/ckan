# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as tk


class ExampleIDatasetFormPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IDatasetForm)

    def create_package_schema(self):
        # let's grab the default schema in our plugin
        schema = super(ExampleIDatasetFormPlugin, self).create_package_schema()
        # our custom field
        schema.update({
            u'custom_text': [tk.get_validator(u'ignore_missing'),
                             tk.get_converter(u'convert_to_extras')]
        })
        return schema

    def update_package_schema(self):
        schema = super(ExampleIDatasetFormPlugin, self).update_package_schema()
        # our custom field
        schema.update({
            u'custom_text': [tk.get_validator(u'ignore_missing'),
                             tk.get_converter(u'convert_to_extras')]
        })
        return schema

    def show_package_schema(self):
        schema = super(ExampleIDatasetFormPlugin, self).show_package_schema()
        schema.update({
            u'custom_text': [tk.get_converter(u'convert_from_extras'),
                             tk.get_validator(u'ignore_missing')]
        })
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return [u'fancy_type']
