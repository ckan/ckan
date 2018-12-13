# encoding: utf-8

import mock
import nose

import sqlalchemy.exc

import ckan.plugins as p
import ckan.lib.jobs as jobs
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

import ckanext.datastore.backend.postgres as db
import ckanext.datastore.backend as backend
from ckanext.datastore.tests.helpers import DatastoreFunctionalTestBase

assert_equal = nose.tools.assert_equal


class TestCreateIndexes(object):
    @helpers.change_config('ckan.datastore.default_fts_index_method', None)
    def test_creates_fts_index_using_gist_by_default(self):
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('_full_text', connection, resource_id,
                                      method='gist')

    @helpers.change_config('ckan.datastore.default_fts_index_method', 'gin')
    def test_default_fts_index_method_can_be_overwritten_by_config_var(self):
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('_full_text', connection, resource_id,
                                      method='gin')

    @helpers.change_config('ckan.datastore.default_fts_lang', None)
    @mock.patch('ckanext.datastore.backend.postgres._get_fields')
    def test_creates_fts_index_on_all_fields_except_dates_nested_and_arrays_with_english_as_default(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'text', 'type': 'text'},
            {'id': 'number', 'type': 'number'},
            {'id': 'nested', 'type': 'nested'},
            {'id': 'date', 'type': 'date'},
            {'id': 'text array', 'type': 'text[]'},
            {'id': 'timestamp', 'type': 'timestamp'},
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('text', connection, resource_id, 'english')
        self._assert_created_index_on('number', connection, resource_id, 'english', cast=True)

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    @mock.patch('ckanext.datastore.backend.postgres._get_fields')
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_with_config_var(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('foo', connection, resource_id, 'simple')

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    @mock.patch('ckanext.datastore.backend.postgres._get_fields')
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_using_lang_param(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
            'lang': 'french',
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('foo', connection, resource_id, 'french')

    def _assert_created_index_on(self, field, connection, resource_id,
                                 lang=None, cast=False, method='gist'):
        field = u'"{0}"'.format(field)
        if cast:
            field = u'cast({0} AS text)'.format(field)
        if lang is not None:
            sql_str = (u'ON "resource_id" '
                       u'USING {method}(to_tsvector(\'{lang}\', {field}))')
            sql_str = sql_str.format(method=method, lang=lang, field=field)
        else:
            sql_str = u'USING {method}({field})'.format(method=method,
                                                        field=field)

        calls = connection.execute.call_args_list
        was_called = [call for call in calls if call[0][0].find(sql_str) != -1]

        assert was_called, ("Expected 'connection.execute' to have been "
                            "called with a string containing '%s'" % sql_str)


@mock.patch("ckanext.datastore.backend.postgres._get_fields")
def test_upsert_with_insert_method_and_invalid_data(
        mock_get_fields_function):
    """upsert_data() should raise InvalidDataError if given invalid data.

    If the type of a field is numeric and upsert_data() is given a whitespace
    value like "   ", it should raise DataError.

    In this case we're testing with "method": "insert" in the data_dict.

    """
    mock_connection = mock.Mock()
    mock_connection.execute.side_effect = sqlalchemy.exc.DataError(
        "statement", "params", "orig", connection_invalidated=False)

    context = {
        "connection": mock_connection,
    }
    data_dict = {
        "fields": [{"id": "value", "type": "numeric"}],
        "records": [
            {"value": 0},
            {"value": 1},
            {"value": 2},
            {"value": 3},
            {"value": "   "},  # Invalid numeric value.
            {"value": 5},
            {"value": 6},
            {"value": 7},
        ],
        "method": "insert",
        "resource_id": "fake-resource-id",
    }

    mock_get_fields_function.return_value = data_dict["fields"]

    nose.tools.assert_raises(
        backend.InvalidDataError, db.upsert_data, context, data_dict)


class TestGetAllResourcesIdsInDatastore(DatastoreFunctionalTestBase):
    def test_get_all_resources_ids_in_datastore(self):
        resource_in_datastore = factories.Resource()
        resource_not_in_datastore = factories.Resource()
        data = {
            'resource_id': resource_in_datastore['id'],
            'force': True,
        }
        helpers.call_action('datastore_create', **data)

        resource_ids = backend.get_all_resources_ids_in_datastore()

        assert resource_in_datastore['id'] in resource_ids
        assert resource_not_in_datastore['id'] not in resource_ids


def datastore_job(res_id, value):
    '''
    A background job that uses the Datastore.
    '''
    app = helpers._get_test_app()
    p.load('datastore')
    data = {
        'resource_id': res_id,
        'method': 'insert',
        'records': [{'value': value}],
    }

    with app.flask_app.test_request_context():
        helpers.call_action('datastore_upsert', **data)


class TestBackgroundJobs(helpers.RQTestBase, DatastoreFunctionalTestBase):
    '''
    Test correct interaction with the background jobs system.
    '''
    def test_worker_datastore_access(self):
        '''
        Test DataStore access from within a worker.
        '''
        pkg = factories.Dataset()
        data = {
            'resource': {
                'package_id': pkg['id'],
            },
            'fields': [{'id': 'value', 'type': 'int'}],
        }

        with self._get_test_app().flask_app.test_request_context():
            table = helpers.call_action('datastore_create', **data)
        res_id = table['resource_id']
        for i in range(3):
            self.enqueue(datastore_job, args=[res_id, i])
        jobs.Worker().work(burst=True)
        # Aside from ensuring that the job succeeded, this also checks
        # that accessing the Datastore still works in the main process.
        result = helpers.call_action('datastore_search', resource_id=res_id)
        assert_equal([0, 1, 2], [r['value'] for r in result['records']])
