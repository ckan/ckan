import mock
import nose

import sqlalchemy.exc

import ckan.new_tests.helpers as helpers

import ckanext.datastore.db as db

assert_equal = nose.tools.assert_equal


class TestCreateIndexes(object):
    def test_creates_fts_index_by_default(self):
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('_full_text', connection, resource_id)

    @helpers.change_config('ckan.datastore.default_fts_lang', None)
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_with_english_as_default(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
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

        self._assert_created_index_on('foo', connection, resource_id, 'english')

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_with_config_var(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
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
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_using_lang_param(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
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

    def _assert_created_index_on(self, field, connection, resource_id, lang=None):
        if lang is not None:
            sql_str = u'ON "resource_id" USING gist(to_tsvector(\'{lang}\', \'{field}\'))'
            sql_str = sql_str.format(lang=lang, field=field)
        else:
            sql_str = u'USING gist({field})'.format(field=field)

        calls = connection.execute.call_args_list
        was_called = [call for call in calls if call[0][0].find(sql_str) != -1]

        assert was_called, ("Expected 'connection.execute' to have been ",
                            "called with a string containing '%s'" % sql_str)


@mock.patch("ckanext.datastore.db._get_fields")
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
        db.InvalidDataError, db.upsert_data, context, data_dict)
