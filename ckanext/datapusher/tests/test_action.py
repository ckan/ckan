# encoding: utf-8

import datetime

from nose.tools import eq_
import mock

import ckan.plugins as p
from ckan.tests import helpers, factories


class TestDataPusherAction(object):

    @classmethod
    def setup_class(cls):

        cls.app = helpers._get_test_app()

        if not p.plugin_loaded('datastore'):
            p.load('datastore')
        if not p.plugin_loaded('datapusher'):
            p.load('datapusher')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):

        p.unload('datapusher')
        p.unload('datastore')

        helpers.reset_db()

    def _pending_task(self, resource_id):
        return {
            'entity_id': resource_id,
            'entity_type': 'resource',
            'task_type': 'datapusher',
            'last_updated': str(datetime.datetime.utcnow()),
            'state': 'pending',
            'key': 'datapusher',
            'value': '{}',
            'error': '{}',
        }

    @helpers.mock_action('datapusher_submit')
    def test_submit(self, mock_datapusher_submit):
        dataset = factories.Dataset()

        assert not mock_datapusher_submit.called

        helpers.call_action('resource_create', {},
                            package_id=dataset['id'],
                            url='http://example.com/file.csv',
                            format='CSV')

        assert mock_datapusher_submit.called

    @helpers.mock_action('datapusher_submit')
    def test_submit_when_url_changes(self, mock_datapusher_submit):
        dataset = factories.Dataset()

        resource = helpers.call_action('resource_create', {},
                                       package_id=dataset['id'],
                                       url='http://example.com/file.pdf',
                                       )

        assert not mock_datapusher_submit.called

        helpers.call_action('resource_update', {},
                            id=resource['id'],
                            package_id=dataset['id'],
                            url='http://example.com/file.csv',
                            format='CSV'
                            )

        assert mock_datapusher_submit.called

    @helpers.mock_action('datapusher_submit')
    def test_does_not_submit_while_ongoing_job(self, mock_datapusher_submit):
        dataset = factories.Dataset()

        resource = helpers.call_action('resource_create', {},
                                       package_id=dataset['id'],
                                       url='http://example.com/file.CSV',
                                       format='CSV'
                                       )

        assert mock_datapusher_submit.called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Create a task with a state pending to mimic an ongoing job
        # on the DataPusher
        helpers.call_action('task_status_update', {},
                            **self._pending_task(resource['id']))

        # Update the resource
        helpers.call_action('resource_update', {},
                            id=resource['id'],
                            package_id=dataset['id'],
                            url='http://example.com/file.csv',
                            format='CSV',
                            description='Test',
                            )
        # Not called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

    @helpers.mock_action('datapusher_submit')
    def test_resubmits_if_url_changes_in_the_meantime(
            self, mock_datapusher_submit):
        dataset = factories.Dataset()

        resource = helpers.call_action('resource_create', {},
                                       package_id=dataset['id'],
                                       url='http://example.com/file.csv',
                                       format='CSV'
                                       )

        assert mock_datapusher_submit.called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Create a task with a state pending to mimic an ongoing job
        # on the DataPusher
        task = helpers.call_action('task_status_update', {},
                                   **self._pending_task(resource['id']))

        # Update the resource, set a new URL
        helpers.call_action('resource_update', {},
                            id=resource['id'],
                            package_id=dataset['id'],
                            url='http://example.com/another.file.csv',
                            format='CSV',
                            )
        # Not called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Call datapusher_hook with state complete, to mock the DataPusher
        # finishing the job and telling CKAN
        data_dict = {
            'metadata': {
                'resource_id': resource['id'],
                'original_url': 'http://example.com/file.csv',
                'task_created': task['last_updated'],
            },
            'status': 'complete',
        }
        helpers.call_action('datapusher_hook', {}, **data_dict)

        # datapusher_submit was called again
        eq_(len(mock_datapusher_submit.mock_calls), 2)

    @helpers.mock_action('datapusher_submit')
    def test_resubmits_if_upload_changes_in_the_meantime(
            self, mock_datapusher_submit):
        dataset = factories.Dataset()

        resource = helpers.call_action('resource_create', {},
                                       package_id=dataset['id'],
                                       url='http://example.com/file.csv',
                                       format='CSV'
                                       )

        assert mock_datapusher_submit.called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Create a task with a state pending to mimic an ongoing job
        # on the DataPusher
        task = helpers.call_action('task_status_update', {},
                                   **self._pending_task(resource['id']))

        # Update the resource, set a new last_modified (changes on file upload)
        helpers.call_action(
            'resource_update', {},
            id=resource['id'],
            package_id=dataset['id'],
            url='http://example.com/file.csv',
            format='CSV',
            last_modified=datetime.datetime.utcnow().isoformat()
        )
        # Not called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Call datapusher_hook with state complete, to mock the DataPusher
        # finishing the job and telling CKAN
        data_dict = {
            'metadata': {
                'resource_id': resource['id'],
                'original_url': 'http://example.com/file.csv',
                'task_created': task['last_updated'],
            },
            'status': 'complete',
        }
        helpers.call_action('datapusher_hook', {}, **data_dict)

        # datapusher_submit was called again
        eq_(len(mock_datapusher_submit.mock_calls), 2)

    @helpers.mock_action('datapusher_submit')
    def test_does_not_resubmit_if_a_resource_field_changes_in_the_meantime(
            self, mock_datapusher_submit):
        dataset = factories.Dataset()

        resource = helpers.call_action('resource_create', {},
                                       package_id=dataset['id'],
                                       url='http://example.com/file.csv',
                                       format='CSV'
                                       )

        assert mock_datapusher_submit.called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Create a task with a state pending to mimic an ongoing job
        # on the DataPusher
        task = helpers.call_action('task_status_update', {},
                                   **self._pending_task(resource['id']))

        # Update the resource, set a new description
        helpers.call_action('resource_update', {},
                            id=resource['id'],
                            package_id=dataset['id'],
                            url='http://example.com/file.csv',
                            format='CSV',
                            description='Test',
                            )
        # Not called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Call datapusher_hook with state complete, to mock the DataPusher
        # finishing the job and telling CKAN
        data_dict = {
            'metadata': {
                'resource_id': resource['id'],
                'original_url': 'http://example.com/file.csv',
                'task_created': task['last_updated'],
            },
            'status': 'complete',
        }
        helpers.call_action('datapusher_hook', {}, **data_dict)

        # Not called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

    @helpers.mock_action('datapusher_submit')
    def test_does_not_resubmit_if_a_dataset_field_changes_in_the_meantime(
            self, mock_datapusher_submit):
        dataset = factories.Dataset()

        resource = helpers.call_action('resource_create', {},
                                       package_id=dataset['id'],
                                       url='http://example.com/file.csv',
                                       format='CSV'
                                       )

        assert mock_datapusher_submit.called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Create a task with a state pending to mimic an ongoing job
        # on the DataPusher
        task = helpers.call_action('task_status_update', {},
                                   **self._pending_task(resource['id']))

        # Update the parent dataset
        helpers.call_action('package_update', {},
                            id=dataset['id'],
                            notes='Test notes',
                            resources=[resource]
                            )
        # Not called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

        # Call datapusher_hook with state complete, to mock the DataPusher
        # finishing the job and telling CKAN
        data_dict = {
            'metadata': {
                'resource_id': resource['id'],
                'original_url': 'http://example.com/file.csv',
                'task_created': task['last_updated'],
            },
            'status': 'complete',
        }
        helpers.call_action('datapusher_hook', {}, **data_dict)

        # Not called
        eq_(len(mock_datapusher_submit.mock_calls), 1)

    def test_duplicated_tasks(self):
        def submit(res, user):
            return helpers.call_action(
                'datapusher_submit', context=dict(user=user['name']),
                resource_id=res['id'])

        user = factories.User()
        res = factories.Resource(user=user)

        with self.app.flask_app.test_request_context():
            with mock.patch('requests.post') as r_mock:
                r_mock().json = mock.Mock(
                    side_effect=lambda: dict.fromkeys(
                        ['job_id', 'job_key']))
                r_mock.reset_mock()
                submit(res, user)
                submit(res, user)

                eq_(1, r_mock.call_count)
