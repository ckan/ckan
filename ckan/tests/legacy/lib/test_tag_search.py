# encoding: utf-8

from ckan.tests.legacy import is_search_supported
import ckan.lib.search as search
from ckan import model
from ckan.lib.create_test_data import CreateTestData
import pytest


class TestTagSearch(object):
    @pytest.fixture(autouse=True)
    @pytest.mark.skipif(
        not is_search_supported(), reason="Search not supported"
    )
    def initial_data(self, clean_db, clean_index):
        CreateTestData.create()

    def test_good_search_query(self):
        result = search.query_for(model.Tag).run(query="r")
        assert result["count"] == 1, result
        assert "russian" in result["results"], result

        result = search.query_for(model.Tag).run(query="s")
        assert result["count"] == 2, result
        assert "russian" in result["results"], result
        assert "tolstoy" in result["results"], result

    def test_good_search_queries(self):
        result = search.query_for(model.Tag).run(query=["r", "s"])
        assert result["count"] == 1, result
        assert "russian" in result["results"], result

    def test_bad_search_query(self):
        result = search.query_for(model.Tag).run(query="asdf")
        assert result["count"] == 0, result

    def test_search_with_capital_letter_in_tagname(self):
        """
        Asserts that it doesn't matter if the tagname has capital letters in it.
        """
        result = search.query_for(model.Tag).run(query="lexible")
        assert "Flexible \u30a1" in result["results"]

    def test_search_with_capital_letter_in_search_query(self):
        """
        Asserts that search works with a capital letter in the search query.
        """
        result = search.query_for(model.Tag).run(query="Flexible")
        assert "Flexible \u30a1" in result["results"]

    def test_search_with_unicode_in_search_query(self):
        """
        Asserts that search works with a unicode character above \u00ff.
        """
        result = search.query_for(model.Tag).run(query=" \u30a1")
        assert "Flexible \u30a1" in result["results"]

    def test_search_is_case_insensitive(self):
        result = search.query_for(model.Tag).run(query="flexible")
        assert "Flexible \u30a1" in result["results"]

    def test_good_search_fields(self):
        result = search.query_for(model.Tag).run(fields={"tags": "r"})
        assert result["count"] == 1, result
        assert "russian" in result["results"], result

        result = search.query_for(model.Tag).run(fields={"tags": "s"})
        assert result["count"] == 2, result
        assert "russian" in result["results"], result
        assert "tolstoy" in result["results"], result

    def test_bad_search_fields(self):
        result = search.query_for(model.Tag).run(fields={"tags": "asdf"})
        assert result["count"] == 0, result
