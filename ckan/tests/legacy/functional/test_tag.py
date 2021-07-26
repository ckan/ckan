# encoding: utf-8

import json
import pytest
from ckan.tests.legacy import CreateTestData, url_for


HTTP_MOVED_PERMANENTLY = 301


@pytest.fixture(autouse=True)
def initial_data(clean_db):
    CreateTestData.create()


def test_autocomplete(app):
    offset = url_for("api.tag_autocomplete", ver=2)
    res = app.get(offset)
    assert "[]" in res
    offset = url_for("api.tag_autocomplete", incomplete="russian", ver=2)
    res = app.get(offset)
    assert "russian" in res
    assert "tolstoy" not in res
    offset = url_for("api.tag_autocomplete", incomplete="tolstoy", ver=2)
    res = app.get(offset)
    assert "russian" not in res
    assert "tolstoy" in res


def test_autocomplete_with_capital_letter_in_search_term(app):
    offset = url_for("api.tag_autocomplete", incomplete="Flex", ver=2)
    res = app.get(offset)
    data = json.loads(res.body)
    assert u"Flexible \u30a1" in data["ResultSet"]["Result"][0].values()


def test_autocomplete_with_space_in_search_term(app):
    offset = url_for("api.tag_autocomplete", incomplete="Flexible ", ver=2)
    res = app.get(offset)
    data = json.loads(res.body)
    assert u"Flexible \u30a1" in data["ResultSet"]["Result"][0].values()


def test_autocomplete_with_unicode_in_search_term(app):
    offset = url_for("api.tag_autocomplete", incomplete=u"ible \u30a1", ver=2)
    res = app.get(offset)
    data = json.loads(res.body)
    assert u"Flexible \u30a1" in data["ResultSet"]["Result"][0].values()
