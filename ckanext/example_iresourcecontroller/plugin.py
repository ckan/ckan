# encoding: utf-8

from collections import defaultdict
import ckan.plugins as plugins


class ExampleIResourceControllerPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IResourceController)

    def __init__(self, *args, **kwargs):
        self.counter = defaultdict(int)

    def before_create(self, context, resource):
        self.counter['before_create'] += 1

    def after_create(self, context, resource):
        self.counter['after_create'] += 1

    def before_update(self, context, current, resource):
        self.counter['before_update'] += 1

    def after_update(self, context, resource):
        self.counter['after_update'] += 1

    def before_delete(self, context, resource, resources):
        self.counter['before_delete'] += 1

    def after_delete(self, context, resources):
        self.counter['after_delete'] += 1

    def before_show(self, resource):
        self.counter['before_show'] += 1
