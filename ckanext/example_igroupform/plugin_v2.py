# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk


def fancy_route(group_type, is_organization):
    return u'Hello, {}'.format(group_type)


def fancy_new_route(group_type, is_organization):
    return u'Hello, new {}'.format(group_type)


class ExampleIGroupFormPlugin(plugins.SingletonPlugin, tk.DefaultGroupForm):
    plugins.implements(plugins.IGroupForm, inherit=False)

    def is_fallback(self):
        return False

    def group_types(self):
        return [u'fancy_type']

    def prepare_group_blueprint(self, package_type, bp):
        bp.add_url_rule(u'/fancy-route', view_func=fancy_route)
        bp.add_url_rule(u'/new', view_func=fancy_new_route)
        return bp
