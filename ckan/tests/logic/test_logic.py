# -*- coding: utf-8 -*-

import pytest

from ckan import logic
import ckan.lib.navl.dictization_functions as df


def test_tuplize_dict():

    data_dict = {
        "author": "Test Author",
        "extras__0__key": "extra1",
        "extras__0__value": "value1",
        "extras__1__key": "extra2",
        "extras__1__value": "value2",
        "extras__2__key": "extra3",
        "extras__2__value": "value3",
        "extras__3__key": "",
        "extras__3__value": "",
        "groups__0__id": "5a65eae8-ef2b-4a85-8022-d9e5a71ad074",
        "name": "test-title",
        "notes": "Test desc",
        "owner_org": "5a65eae8-ef2b-4a85-8022-d9e5a71ad074",
        "private": "True",
        "tag_string": "economy,climate",
        "title": "Test title",
    }

    expected = {
        ("author",): "Test Author",
        ("extras", 0, "key"): "extra1",
        ("extras", 0, "value"): "value1",
        ("extras", 1, "key"): "extra2",
        ("extras", 1, "value"): "value2",
        ("extras", 2, "key"): "extra3",
        ("extras", 2, "value"): "value3",
        ("extras", 3, "key"): "",
        ("extras", 3, "value"): "",
        ("groups", 0, "id"): "5a65eae8-ef2b-4a85-8022-d9e5a71ad074",
        ("name",): "test-title",
        ("notes",): "Test desc",
        ("owner_org",): "5a65eae8-ef2b-4a85-8022-d9e5a71ad074",
        ("private",): "True",
        ("tag_string",): "economy,climate",
        ("title",): "Test title",
    }

    assert logic.tuplize_dict(data_dict) == expected


def test_tuplize_dict_random_indexes():

    data_dict = {
        "extras__22__key": "extra2",
        "extras__22__value": "value2",
        "extras__1__key": "extra1",
        "extras__1__value": "value1",
        "extras__245566546__key": "extra3",
        "extras__245566546__value": "value3",
        "groups__13__id": "group2",
        "groups__1__id": "group1",
        "groups__13__nested__7__name": "latter",
        "groups__13__nested__2__name": "former",
    }

    expected = {
        ("extras", 0, "key"): "extra1",
        ("extras", 0, "value"): "value1",
        ("extras", 1, "key"): "extra2",
        ("extras", 1, "value"): "value2",
        ("extras", 2, "key"): "extra3",
        ("extras", 2, "value"): "value3",
        ("groups", 0, "id"): "group1",
        ("groups", 1, "id"): "group2",
        ("groups", 1, "nested", 0, "name"): "former",
        ("groups", 1, "nested", 1, "name"): "latter",
    }

    assert logic.tuplize_dict(data_dict) == expected


def test_tuplize_dict_wrong_index():

    with pytest.raises(df.DataError):
        data_dict = {
            "extras__2a__key": "extra",
        }
        logic.tuplize_dict(data_dict)
