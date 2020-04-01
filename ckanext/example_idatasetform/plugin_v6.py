# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as tk


def fancy_route(package_type):
    return u'Hello, {}'.format(package_type)


def fancy_new_route(package_type):
    return u'Hello, new {}'.format(package_type)


def fancy_resource_route(package_type, id):
    return u'Hello, {}:{}'.format(package_type, id)


class ExampleIDatasetFormPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IDatasetForm)

    def is_fallback(self):
        return False

    def package_types(self):
        return [u'fancy_type']

    def prepare_dataset_blueprint(self, package_type, bp):
        bp.add_url_rule(u'/fancy-route', view_func=fancy_route)
        bp.add_url_rule(u'/new', view_func=fancy_new_route)
        return bp

    def prepare_resource_blueprint(self, package_type, bp):
        bp.add_url_rule(u'/new', view_func=fancy_resource_route)
        return bp
