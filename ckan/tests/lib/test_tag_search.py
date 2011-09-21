from nose.tools import assert_raises
from ckan.tests import *
from ckan.tests import is_search_supported
import ckan.lib.search as search
from ckan import model
from ckan.lib.create_test_data import CreateTestData

class TestTagSearch(object):
    @classmethod
    def setup_class(self):
        if not is_search_supported():
            raise SkipTest("Search not supported")
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_good_search_query(self):
        result = search.query_for(model.Tag).run(query=u'ru')
        assert result['count'] == 1, result
        assert 'russian' in result['results'], result

        result = search.query_for(model.Tag).run(query=u's')
        assert result['count'] == 2, result
        assert 'russian' in result['results'], result
        assert 'tolstoy' in result['results'], result

    def test_bad_search_query(self):
        result = search.query_for(model.Tag).run(query=u'asdf')
        assert result['count'] == 0, result

    def test_good_search_fields(self):
        result = search.query_for(model.Tag).run(fields={'tags': u'ru'})
        assert result['count'] == 1, result
        assert 'russian' in result['results'], result

        result = search.query_for(model.Tag).run(fields={'tags': u's'})
        assert result['count'] == 2, result
        assert 'russian' in result['results'], result
        assert 'tolstoy' in result['results'], result

    def test_bad_search_fields(self):
        result = search.query_for(model.Tag).run(fields={'tags': u'asdf'})
        assert result['count'] == 0, result
