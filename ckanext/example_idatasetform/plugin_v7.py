# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as tk


class ExampleIDatasetFormPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IConfigurer)
    p.implements(p.IDatasetForm)

    def update_config(self, config):
        tk.add_template_directory(config, 'templates')

    def is_fallback(self):
        return False

    def package_types(self):
        return [u'first', 'second']

    def read_template(self, options):
        return '{}/read.html'.format(
            options['package_type']
        )

    def new_template(self):
        return ['first/new.html', 'first/read.html']
