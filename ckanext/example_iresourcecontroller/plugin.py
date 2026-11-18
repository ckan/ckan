# encoding: utf-8

from collections import defaultdict
from typing import Any
import ckan.plugins as plugins


class ExampleIResourceControllerPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IResourceController)

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.counter = defaultdict(int)

    def before_resource_create(self, context: Any, resource: Any):
        self.counter['before_resource_create'] += 1

    def after_resource_create(self, context: Any, resource: Any):
        self.counter['after_resource_create'] += 1

    def before_resource_update(
            self, context: Any, current: Any, resource: Any):
        self.counter['before_resource_update'] += 1

    def after_resource_update(self, context: Any, resource: Any):
        self.counter['after_resource_update'] += 1
        import ckan.logic as logic
        import ckan.model as model

        self.last_diagnostics = {
            'context_use_cache': context.get('use_cache'),
            'context_defer_commit': context.get('defer_commit'),
            'hook_resource_url': resource.get('url'),
            'hook_resource_schema': resource.get('schema'),
            'hook_resource_extra': resource.get('my_extra'),
        }

        # Same-session read via resource_show using context
        try:
            same_res = logic.get_action('resource_show')(context, {'id': resource['id']})
            self.last_diagnostics['same_session_res'] = same_res
            self.last_diagnostics['same_session_schema'] = same_res.get('schema')
            self.last_diagnostics['same_session_extra'] = same_res.get('my_extra')
        except Exception as e:
            self.last_diagnostics['same_session_res_error'] = str(e)

        # Fresh-connection / separate-session direct DB read
        fresh_session = model.meta.create_local_session()
        try:
            fresh_db_res = fresh_session.get(model.Resource, resource['id'])
            self.last_diagnostics['fresh_session_db_url'] = (
                fresh_db_res.url if fresh_db_res else None
            )
            self.last_diagnostics['fresh_session_extra'] = (
                fresh_db_res.extras.get('my_extra') if fresh_db_res and fresh_db_res.extras else None
            )
        finally:
            fresh_session.close()


    def before_resource_delete(
            self, context: Any, resource: Any, resources: Any):
        self.counter['before_resource_delete'] += 1

    def after_resource_delete(self, context: Any, resources: Any):
        self.counter['after_resource_delete'] += 1

    def before_resource_show(self, resource: Any):
        self.counter['before_resource_show'] += 1
