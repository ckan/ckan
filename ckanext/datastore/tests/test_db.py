import mock
import nose

import ckan.new_tests.helpers as helpers

import ckanext.datastore.db as db

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
    @mock.patch('ckanext.datastore.db._get_fields')
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
    @mock.patch('ckanext.datastore.db._get_fields')
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
    @mock.patch('ckanext.datastore.db._get_fields')
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


class TestJsonGetValues(object):
    def test_returns_empty_list_if_called_with_none(self):
        assert_equal(db.json_get_values(None), [])

    def test_returns_list_with_value_if_called_with_string(self):
        assert_equal(db.json_get_values('foo'), ['foo'])

    def test_returns_list_with_only_the_original_truthy_values_if_called(self):
        data = [None, 'foo', 42, 'bar', {}, []]
        assert_equal(db.json_get_values(data), ['foo', '42', 'bar'])

    def test_returns_flattened_list(self):
        data = ['foo', ['bar', ('baz', 42)]]
        assert_equal(db.json_get_values(data), ['foo', 'bar', 'baz', '42'])

    def test_returns_only_truthy_values_from_dict(self):
        data = {'foo': 'bar', 'baz': [42, None, {}, [], 'hey']}
        assert_equal(db.json_get_values(data), ['foo', 'bar', 'baz', '42', 'hey'])
