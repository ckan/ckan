# encoding: utf-8

from collections import defaultdict
from typing import Any
import ckan.plugins as plugins


class ExampleIResourceControllerPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IResourceController)

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.counter = defaultdict(int)

    # this method deliberately uses deprecated `before_create` name instead of
    # `before_resource_create`. Change the name after support for deprecated
    # names is dropped.
    def before_create(self, context: Any, resource: Any):
        self.counter['before_resource_create'] += 1

    def after_resource_create(self, context: Any, resource: Any):
        self.counter['after_resource_create'] += 1

    def before_resource_update(
            self, context: Any, current: Any, resource: Any):
        self.counter['before_resource_update'] += 1

    def after_resource_update(self, context: Any, resource: Any):
        self.counter['after_resource_update'] += 1

    def before_resource_delete(
            self, context: Any, resource: Any, resources: Any):
        self.counter['before_resource_delete'] += 1

    def after_resource_delete(self, context: Any, resources: Any):
        self.counter['after_resource_delete'] += 1

    def before_resource_show(self, resource: Any):
        self.counter['before_resource_show'] += 1
