import datetime
import pytest
import ckan.model as model
from ckan.common import config
import ckan.lib.search as search
import ckan.tests.factories as factories

@pytest.mark.usefixtures("clean_db", "clean_index")
class TestTagQuery(object):
    def create_test_data(self):
        factories.Dataset(tags=[{"name": "russian"}, {"name": "tolstoy"}])
        factories.Dataset(tags=[{"name": "Flexible \u30a1"}])

    def test_good_search_query(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(query=u"ru")
        assert result["count"] == 1, result
        assert "russian" in result["results"]

        result = search.query_for(model.Tag).run(query=u"s")
        assert result["count"] == 2, result
        assert "russian" in result["results"]
        assert "tolstoy" in result["results"]

    def test_good_search_queries(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(query=[u"ru", u"s"])
        assert result["count"] == 1, result
        assert "russian" in result["results"], result

    def test_bad_search_query(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(query=u"asdf")
        assert result["count"] == 0, result

    def test_search_with_capital_letter_in_tagname(self):
        self.create_test_data()
        """
        Asserts that it doesn't matter if the tagname has capital letters in it.
        """
        result = search.query_for(model.Tag).run(query=u"lexible")
        assert u"Flexible \u30a1" in result["results"]

    def test_search_with_capital_letter_in_search_query(self):
        self.create_test_data()
        """
        Asserts that search works with a capital letter in the search query.
        """
        result = search.query_for(model.Tag).run(query=u"Flexible")
        assert u"Flexible \u30a1" in result["results"]

    def test_search_with_unicode_in_search_query(self):
        self.create_test_data()
        """
        Asserts that search works with a unicode character above \u00ff.
        """
        result = search.query_for(model.Tag).run(query=u" \u30a1")
        assert u"Flexible \u30a1" in result["results"]

    def test_search_is_case_insensitive(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(query=u"flexible")
        assert u"Flexible \u30a1" in result["results"]

    def test_good_search_fields(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(fields={"tags": u"ru"})
        assert result["count"] == 1, result
        assert "russian" in result["results"], result

        result = search.query_for(model.Tag).run(fields={"tags": u"s"})
        assert result["count"] == 2, result
        assert "russian" in result["results"], result
        assert "tolstoy" in result["results"], result

    def test_bad_search_fields(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(fields={"tags": u"asdf"})
        assert result["count"] == 0, result
