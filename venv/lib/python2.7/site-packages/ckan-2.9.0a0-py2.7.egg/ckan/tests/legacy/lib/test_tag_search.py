# encoding: utf-8

from nose.tools import assert_raises
from ckan.tests.legacy import *
from ckan.tests.legacy import is_search_supported
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

    def test_good_search_queries(self):
        result = search.query_for(model.Tag).run(query=[u'ru', u's'])
        assert result['count'] == 1, result
        assert 'russian' in result['results'], result

    def test_bad_search_query(self):
        result = search.query_for(model.Tag).run(query=u'asdf')
        assert result['count'] == 0, result

    def test_search_with_capital_letter_in_tagname(self):
        """
        Asserts that it doesn't matter if the tagname has capital letters in it.
        """
        result = search.query_for(model.Tag).run(query=u'lexible')
        assert u'Flexible \u30a1' in result['results']

    def test_search_with_capital_letter_in_search_query(self):
        """
        Asserts that search works with a capital letter in the search query.
        """
        result = search.query_for(model.Tag).run(query=u'Flexible')
        assert u'Flexible \u30a1' in result['results']

    def test_search_with_unicode_in_search_query(self):
        """
        Asserts that search works with a unicode character above \u00ff.
        """
        result = search.query_for(model.Tag).run(query=u' \u30a1')
        assert u'Flexible \u30a1' in result['results']

    def test_search_is_case_insensitive(self):
        result = search.query_for(model.Tag).run(query=u'flexible')
        assert u'Flexible \u30a1' in result['results']
        

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
