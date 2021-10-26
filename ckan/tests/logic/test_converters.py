# encoding: utf-8
"""Unit tests for ckan/logic/converters.py.

"""
from ckan import model
import pytest
import ckan.tests.factories as factories
import ckan.logic.converters as converters


def test_leading_space():
    string = "  http://example.com"
    expected = "http://example.com"
    converted = converters.remove_whitespace(string, {})
    assert expected == converted


def test_trailing_space():
    string = "http://example.com  "
    expected = "http://example.com"
    converted = converters.remove_whitespace(string, {})
    assert expected == converted


def test_space_between():
    string = "http://example.com/space between url "
    expected = "http://example.com/space between url"
    converted = converters.remove_whitespace(string, {})
    assert expected == converted


def test_not_a_string():
    string = 12345
    converted = converters.remove_whitespace(string, {})
    assert string == converted


def test_convert_to_extras_output_unflattened():

    key = ("test_field",)
    data = {("test_field",): "test_value"}
    errors = {}
    context = {}

    converters.convert_to_extras(key, data, errors, context)

    assert data[("extras", 0, "key")] == "test_field"
    assert data[("extras", 0, "value")] == "test_value"

    assert ("extras",) not in data

    assert errors == {}


def test_convert_to_extras_output_unflattened_with_correct_index():

    key = ("test_field",)
    data = {
        ("test_field",): "test_value",
        ("extras", 0, "deleted"): "",
        ("extras", 0, "id"): "",
        ("extras", 0, "key"): "proper_extra",
        ("extras", 0, "revision_timestamp"): "",
        ("extras", 0, "state"): "",
        ("extras", 0, "value"): "proper_extra_value",
    }
    errors = {}
    context = {}

    converters.convert_to_extras(key, data, errors, context)

    assert data[("extras", 0, "key")] == "proper_extra"
    assert data[("extras", 0, "value")] == "proper_extra_value"
    assert data[("extras", 1, "key")] == "test_field"
    assert data[("extras", 1, "value")] == "test_value"

    assert ("extras",) not in data

    assert errors == {}


@pytest.mark.usefixtures("non_clean_db")
def test_convert_to_tags():
    tag_name = factories.Tag.stub().name
    vocab = factories.Vocabulary(tags=[{"name": tag_name}])
    key = ("vocab_tags",)
    data = {key: tag_name}
    context = {"model": model, "session": model.Session}
    converters.convert_to_tags(vocab["name"])(key, data, [], context)

    assert data[("tags", 0, "name")] == tag_name
    assert data[("tags", 0, "vocabulary_id")] == vocab["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_convert_from_tags():
    tag_name1 = factories.Tag.stub().name
    tag_name2 = factories.Tag.stub().name
    vocab = factories.Vocabulary(
        tags=[
            {"name": tag_name1},
            {"name": tag_name2},
        ]
    )
    key = "tags"
    data = {
        ("tags", 0, "__extras"): {
            "name": tag_name1,
            "vocabulary_id": vocab["id"],
        },
        ("tags", 1, "__extras"): {
            "name": tag_name2,
            "vocabulary_id": vocab["id"],
        },
    }
    errors = []
    context = {"model": model, "session": model.Session}
    converters.convert_from_tags(vocab["name"])(key, data, errors, context)
    assert tag_name1 in data["tags"]
    assert tag_name2 in data["tags"]


@pytest.mark.usefixtures("non_clean_db")
def test_free_tags_only():
    tag_name1 = factories.Tag.stub().name
    tag_name2 = factories.Tag.stub().name

    vocab = factories.Vocabulary(
        tags=[
            {"name": tag_name1},
            {"name": tag_name2},
        ]
    )
    key = ("tags", 0, "__extras")
    data = {
        ("tags", 0, "__extras"): {
            "name": tag_name1,
            "vocabulary_id": vocab["id"],
        },
        ("tags", 0, "vocabulary_id"): vocab["id"],
        ("tags", 1, "__extras"): {"name": tag_name2, "vocabulary_id": None},
        ("tags", 1, "vocabulary_id"): None,
    }
    errors = []
    context = {"model": model, "session": model.Session}
    converters.free_tags_only(key, data, errors, context)
    assert len(data) == 2
    assert ("tags", 1, "vocabulary_id") in data.keys()
    assert ("tags", 1, "__extras") in data.keys()
