# encoding: utf-8

import nose
import mock

import ckan.tests.helpers as helpers
import ckan.plugins as p
import ckanext.datastore.interfaces as interfaces
import ckanext.datastore.plugin as plugin


DatastorePlugin = plugin.DatastorePlugin
assert_equal = nose.tools.assert_equal
assert_raises = nose.tools.assert_raises


class TestPluginLoadingOrder(object):
    def setup(self):
        if p.plugin_loaded('datastore'):
            p.unload('datastore')
        if p.plugin_loaded('sample_datastore_plugin'):
            p.unload('sample_datastore_plugin')

    def teardown(self):
        if p.plugin_loaded('sample_datastore_plugin'):
            p.unload('sample_datastore_plugin')
        if p.plugin_loaded('datastore'):
            p.unload('datastore')

    def test_loading_datastore_first_works(self):
        p.load('datastore')
        p.load('sample_datastore_plugin')
        p.unload('sample_datastore_plugin')
        p.unload('datastore')

    def test_loading_datastore_last_doesnt_work(self):
        # This test is complicated because we can't import
        # ckanext.datastore.plugin before running it. If we did so, the
        # DatastorePlugin class would be parsed which breaks the reason of our
        # test.
        p.load('sample_datastore_plugin')
        thrown_exception = None
        try:
            p.load('datastore')
        except Exception as e:
            thrown_exception = e
        idatastores = [x.__class__.__name__ for x
                       in p.PluginImplementations(interfaces.IDatastore)]
        p.unload('sample_datastore_plugin')

        assert thrown_exception is not None, \
            ('Loading "datastore" after another IDatastore plugin was'
             'loaded should raise DatastoreException')
        assert_equal(thrown_exception.__class__.__name__,
                     plugin.DatastoreException.__name__)
        assert plugin.DatastorePlugin.__name__ not in idatastores, \
            ('You shouldn\'t be able to load the "datastore" plugin after'
             'another IDatastore plugin was loaded')


class TestPluginDatastoreSearch(object):
    @classmethod
    def setup_class(cls):
        p.load('datastore')

    @classmethod
    def teardown_class(cls):
        p.unload('datastore')

    @helpers.change_config('ckan.datastore.default_fts_lang', None)
    def test_english_is_default_fts_language(self):
        expected_ts_query = ', plainto_tsquery(\'english\', \'foo\') "query"'
        data_dict = {
            'q': 'foo',
        }

        result = self._datastore_search(data_dict=data_dict)

        assert_equal(result['ts_query'], expected_ts_query)

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    def test_can_overwrite_default_fts_lang_using_config_variable(self):
        expected_ts_query = ', plainto_tsquery(\'simple\', \'foo\') "query"'
        data_dict = {
            'q': 'foo',
        }

        result = self._datastore_search(data_dict=data_dict)

        assert_equal(result['ts_query'], expected_ts_query)

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    def test_lang_parameter_overwrites_default_fts_lang(self):
        expected_ts_query = ', plainto_tsquery(\'french\', \'foo\') "query"'
        data_dict = {
            'q': 'foo',
            'lang': 'french',
        }

        result = self._datastore_search(data_dict=data_dict)

        assert_equal(result['ts_query'], expected_ts_query)

    def test_fts_rank_column_uses_lang_when_casting_to_tsvector(self):
        expected_select_content = u'to_tsvector(\'french\', cast("country" as text))'
        data_dict = {
            'q': {'country': 'Brazil'},
            'lang': 'french',
        }

        result = self._datastore_search(data_dict=data_dict)

        assert expected_select_content in result['select'][0], result['select']

    def test_adds_fts_on_full_text_field_when_q_is_a_string(self):
        expected_where = [(u'_full_text @@ "query"',)]
        data_dict = {
            'q': 'foo',
        }

        result = self._datastore_search(data_dict=data_dict)

        assert_equal(result['where'], expected_where)

    def test_ignores_fts_searches_on_inexistent_fields(self):
        data_dict = {
            'q': {'inexistent-field': 'value'},
        }

        result = self._datastore_search(data_dict=data_dict, fields_types={})

        assert_equal(result['where'], [])

    @helpers.change_config('ckan.datastore.default_fts_lang', None)
    def test_fts_where_clause_lang_uses_english_by_default(self):
        expected_where = [(u'to_tsvector(\'english\', cast("country" as text))'
                           u' @@ "query country"',)]
        data_dict = {
            'q': {'country': 'Brazil'},
        }
        fields_types = {
            'country': 'text',
        }

        result = self._datastore_search(data_dict=data_dict,
                                        fields_types=fields_types)

        assert_equal(result['where'], expected_where)

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    def test_fts_where_clause_lang_can_be_overwritten_by_config(self):
        expected_where = [(u'to_tsvector(\'simple\', cast("country" as text))'
                           u' @@ "query country"',)]
        data_dict = {
            'q': {'country': 'Brazil'},
        }
        fields_types = {
            'country': 'text',
        }

        result = self._datastore_search(data_dict=data_dict,
                                        fields_types=fields_types)

        assert_equal(result['where'], expected_where)

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    def test_fts_where_clause_lang_can_be_overwritten_using_lang_param(self):
        expected_where = [(u'to_tsvector(\'french\', cast("country" as text))'
                           u' @@ "query country"',)]
        data_dict = {
            'q': {'country': 'Brazil'},
            'lang': 'french',
        }
        fields_types = {
            'country': 'text',
        }

        result = self._datastore_search(data_dict=data_dict,
                                        fields_types=fields_types)

        assert_equal(result['where'], expected_where)

    @mock.patch('ckanext.datastore.helpers.should_fts_index_field_type')
    def test_fts_adds_where_clause_on_full_text_when_querying_non_indexed_fields(self, should_fts_index_field_type):
        should_fts_index_field_type.return_value = False
        expected_where = [('_full_text @@ "query country"',),
                          (u'to_tsvector(\'english\', cast("country" as text))'
                           u' @@ "query country"',)]
        data_dict = {
            'q': {'country': 'Brazil'},
            'lang': 'english',
        }
        fields_types = {
            'country': 'non-indexed field type',
        }

        result = self._datastore_search(data_dict=data_dict,
                                        fields_types=fields_types)

        assert_equal(result['where'], expected_where)

    def _datastore_search(self, context={}, data_dict={}, fields_types={}, query_dict={}):
        _query_dict = {
            'select': [],
            'sort': [],
            'where': [],
        }
        _query_dict.update(query_dict)

        return DatastorePlugin().datastore_search(context, data_dict,
                                                  fields_types, _query_dict)
