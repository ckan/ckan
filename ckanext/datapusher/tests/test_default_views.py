# encoding: utf-8

import datetime
import nose

import ckan.plugins as p
from ckan.tests.legacy import is_datastore_supported

from ckan.tests import helpers, factories

assert_equals = nose.tools.assert_equals


class TestDatapusherResourceViews(object):

    @classmethod
    def setup_class(cls):
        if not is_datastore_supported():
            raise nose.SkipTest('Datastore not supported')
        if not p.plugin_loaded('datastore'):
            p.load('datastore')
        if not p.plugin_loaded('datapusher'):
            p.load('datapusher')
        if not p.plugin_loaded('recline_grid_view'):
            p.load('recline_grid_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('datapusher')
        p.unload('datastore')
        p.unload('recline_grid_view')

    @helpers.change_config('ckan.views.default_views', 'recline_grid_view')
    def test_datapusher_creates_default_views_on_complete(self):

        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset['id'])

        # Push data directly to the DataStore for the resource to be marked as
        # `datastore_active=True`, so the grid view can be created
        data = {
            'resource_id': resource['id'],
            'fields': [{'id': 'a', 'type': 'text'},
                       {'id': 'b', 'type': 'text'}],
            'records': [{'a': '1', 'b': '2'}, ],
            'force': True,
        }
        helpers.call_action('datastore_create', **data)

        # Create a task for `datapusher_hook` to update
        task_dict = {
            'entity_id': resource['id'],
            'entity_type': 'resource',
            'task_type': 'datapusher',
            'key': 'datapusher',
            'value': '{"job_id": "my_id", "job_key":"my_key"}',
            'last_updated': str(datetime.datetime.now()),
            'state': 'pending'
        }
        helpers.call_action('task_status_update', context={}, **task_dict)

        # Call datapusher_hook with a status of complete to trigger the
        # default views creation
        params = {
            'status': 'complete',
            'metadata': {'resource_id': resource['id']}
        }

        helpers.call_action('datapusher_hook', context={}, **params)

        views = helpers.call_action('resource_view_list', id=resource['id'])

        assert_equals(len(views), 1)
        assert_equals(views[0]['view_type'], 'recline_grid_view')

    @helpers.change_config('ckan.views.default_views', 'recline_grid_view')
    def test_datapusher_does_not_create_default_views_on_pending(self):

        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset['id'])

        # Push data directly to the DataStore for the resource to be marked as
        # `datastore_active=True`, so the grid view can be created
        data = {
            'resource_id': resource['id'],
            'fields': [{'id': 'a', 'type': 'text'},
                       {'id': 'b', 'type': 'text'}],
            'records': [{'a': '1', 'b': '2'}, ],
            'force': True,
        }
        helpers.call_action('datastore_create', **data)

        # Create a task for `datapusher_hook` to update
        task_dict = {
            'entity_id': resource['id'],
            'entity_type': 'resource',
            'task_type': 'datapusher',
            'key': 'datapusher',
            'value': '{"job_id": "my_id", "job_key":"my_key"}',
            'last_updated': str(datetime.datetime.now()),
            'state': 'pending'
        }
        helpers.call_action('task_status_update', context={}, **task_dict)

        # Call datapusher_hook with a status of complete to trigger the
        # default views creation
        params = {
            'status': 'pending',
            'metadata': {'resource_id': resource['id']}
        }

        helpers.call_action('datapusher_hook', context={}, **params)

        views = helpers.call_action('resource_view_list', id=resource['id'])

        assert_equals(len(views), 0)
