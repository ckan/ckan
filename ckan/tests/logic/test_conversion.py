# encoding: utf-8
"""Functional tests for converters in ckan/logic/converters.py.

"""
from ckan import model
from ckan.lib.navl.dictization_functions import validate
from ckan.logic.converters import convert_to_extras
from ckan.logic.schema import default_extras_schema


def test_convert_to_extras_field_gets_stored_as_extra():

    data_dict = {"custom_text": "Hi"}

    context = {"model": model, "session": model.Session}

    schema = {
        "custom_text": [convert_to_extras],
        "extras": default_extras_schema(),
    }

    data, errors = validate(data_dict, schema, context)

    assert "extras" in data
    assert len(data["extras"]) == 1
    assert data["extras"][0]["key"] == "custom_text"
    assert data["extras"][0]["value"] == "Hi"


def test_convert_to_extras_field_can_be_combined_with_a_proper_extra():

    data_dict = {
        "custom_text": "Hi",
        "extras": [{"key": "proper_extra", "value": "Bye"}],
    }

    schema = {
        "custom_text": [convert_to_extras],
        "extras": default_extras_schema(),
    }

    context = {"model": model, "session": model.Session}

    data, errors = validate(data_dict, schema, context)

    assert "extras" in data
    assert len(data["extras"]) == 2
    assert sorted([e["key"] for e in data["extras"]]) == [
        "custom_text",
        "proper_extra",
    ]
    assert sorted([e["value"] for e in data["extras"]]) == ["Bye", "Hi"]


def test_convert_to_extras_field_can_be_combined_with_more_extras():

    data_dict = {
        "custom_text": "Hi",
        "extras": [
            {"key": "proper_extra", "value": "Bye"},
            {"key": "proper_extra2", "value": "Bye2"},
        ],
    }

    schema = {
        "custom_text": [convert_to_extras],
        "extras": default_extras_schema(),
    }

    context = {"model": model, "session": model.Session}

    data, errors = validate(data_dict, schema, context)

    assert "extras" in data
    assert len(data["extras"]) == 3
    assert sorted([e["key"] for e in data["extras"]]) == [
        "custom_text",
        "proper_extra",
        "proper_extra2",
    ]
    assert sorted([e["value"] for e in data["extras"]]) == [
        "Bye",
        "Bye2",
        "Hi",
    ]


def test_convert_to_extras_field_can_be_combined_with_extras_deleted():

    data_dict = {
        "custom_text": "Hi",
        "extras": [
            {"key": "proper_extra", "value": "Bye", "deleted": True},
            {"key": "proper_extra2", "value": "Bye2"},
        ],
    }

    schema = {
        "custom_text": [convert_to_extras],
        "extras": default_extras_schema(),
    }

    context = {"model": model, "session": model.Session}

    data, errors = validate(data_dict, schema, context)

    assert "extras" in data
    assert len(data["extras"]) == 3
    assert sorted([e["key"] for e in data["extras"]]) == [
        "custom_text",
        "proper_extra",
        "proper_extra2",
    ]
    assert sorted([e["value"] for e in data["extras"]]) == [
        "Bye",
        "Bye2",
        "Hi",
    ]


def test_convert_to_extras_free_extra_can_not_have_the_same_key():

    data_dict = {
        "custom_text": "Hi",
        "extras": [{"key": "custom_text", "value": "Bye"}],
    }

    schema = {
        "custom_text": [convert_to_extras],
        "extras": default_extras_schema(),
    }

    context = {"model": model, "session": model.Session}

    data, errors = validate(data_dict, schema, context)

    assert "extras" in errors
    assert errors["extras"] == [
        {"key": [u"There is a schema field with the same name"]}
    ]
