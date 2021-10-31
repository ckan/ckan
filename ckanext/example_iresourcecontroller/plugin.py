# encoding: utf-8

from collections import defaultdict
import ckan.plugins as plugins


class ExampleIResourceControllerPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IResourceController)

    def __init__(self, *args, **kwargs):
        self.counter = defaultdict(int)

    def before_resource_create(self, context, resource):
        self.counter['before_resource_create'] += 1

    def after_resource_create(self, context, resource):
        self.counter['after_resource_create'] += 1

    def before_resource_update(self, context, current, resource):
        self.counter['before_resource_update'] += 1

    def after_resource_update(self, context, resource):
        self.counter['after_resource_update'] += 1

    def before_resource_delete(self, context, resource, resources):
        self.counter['before_resource_delete'] += 1

    def after_resource_delete(self, context, resources):
        self.counter['after_resource_delete'] += 1

    def before_resource_show(self, resource):
        self.counter['before_resource_show'] += 1
