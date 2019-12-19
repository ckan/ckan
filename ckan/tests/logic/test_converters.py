# encoding: utf-8
"""Unit tests for ckan/logic/converters.py.

"""
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
