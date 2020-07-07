# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as tk


class ExampleIDatasetFormPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IConfigurer)
    p.implements(p.IDatasetForm)

    def update_config(self, config):
        tk.add_template_directory(config, u'templates')

    def is_fallback(self):
        return False

    def package_types(self):
        return [u'first', u'second']

    def read_template(self, package_type):
        return u'{}/read.html'.format(package_type)

    def new_template(self):
        return [u'first/new.html', u'first/read.html']
