import mock
import nose

import ckan.new_tests.helpers as helpers

import ckanext.datastore.db as db

assert_equal = nose.tools.assert_equal


class TestCreateIndexes(object):
    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_creates_fts_index_by_default(self, _pg_version_is_at_least):
        _pg_version_is_at_least.return_value = True
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        data_dict = {
            'resource_id': 'resource_id',
        }

        db.create_indexes(context, data_dict)

        sql_str = u'CREATE  INDEX  ON "resource_id" USING gist(_full_text)'
        self._assert_created_index_on('_full_text', connection)

    @helpers.change_config('ckan.datastore.default_fts_lang', None)
    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_with_english_as_default(self, _get_fields, _pg_version_is_at_least):
        _pg_version_is_at_least.return_value = True
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        data_dict = {
            'resource_id': 'resource_id',
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('foo', connection, lang='english')

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_with_config_var(self, _get_fields, _pg_version_is_at_least):
        _pg_version_is_at_least.return_value = True
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        data_dict = {
            'resource_id': 'resource_id',
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('foo', connection, lang='simple')

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_using_lang_param(self, _get_fields, _pg_version_is_at_least):
        _pg_version_is_at_least.return_value = True
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        data_dict = {
            'resource_id': 'resource_id',
            'lang': 'french',
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('foo', connection, lang='french')

    def _assert_created_index_on(self, field, connection, lang=None):
        if lang is not None:
            sql_str = u'CREATE  INDEX  ON "resource_id" USING gist(to_tsvector(\'{lang}\', \'{field}\'))'
            sql_str = sql_str.format(lang=lang, field=field)
        else:
            sql_str = u'CREATE  INDEX  ON "resource_id" USING gist({field})'.format(field=field)

        connection.execute.assert_called_with(sql_str)
