# -*- coding: utf-8 -*-

from unittest import mock
import pytest
from typing import cast
from ckan import logic, model
import ckan.lib.navl.dictization_functions as df
from ckan.types import Context
import ckan.tests.factories as factories


def test_model_name_to_class():
    assert logic.model_name_to_class(model, "package") == model.Package
    with pytest.raises(logic.ValidationError):
        logic.model_name_to_class(model, "inexistent_model_name")


def test_check_access_auth_user_obj_is_not_set():

    user_names = ("unknown_user", "", None)
    for user_name in user_names:
        context = {"user": user_name}

        result = logic.check_access("package_search", context)

        assert result
        assert context["__auth_user_obj_checked"]
        assert context["auth_user_obj"] is None


@pytest.mark.usefixtures("non_clean_db")
def test_check_access_auth_user_obj_is_set():
    user = factories.User()
    context = {"user": user["name"]}

    result = logic.check_access("package_create", context)

    assert result
    assert context["__auth_user_obj_checked"]
    assert context["auth_user_obj"].name == user["name"]


@pytest.mark.usefixtures("non_clean_db")
def test_check_access_auth_user_obj_is_not_set_when_ignoring_auth():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": True}

    result = logic.check_access("package_create", context)

    assert result
    assert "__auth_user_obj_checked" not in context
    assert context["auth_user_obj"] is None


@mock.patch("ckan.authz.is_authorized")
def test_user_inside_context_of_check_access(is_authorized: mock.Mock):
    logic.check_access("site_read", {})
    is_authorized.assert_called_once()
    context = is_authorized.call_args[0][1]
    assert context["user"] == ""

    is_authorized.reset_mock()

    logic.check_access("site_read", {"user": "test"})
    context = is_authorized.call_args[0][1]
    assert context["user"] == "test"


def test_get_action_optional_params():

    assert "ckan_version" in logic.get_action("status_show")()


def test_fresh_context():
    """ Test the fresh_context function.
        It should return a new context object only with
        'model', 'session', 'user', 'auth_user_obj', 'ignore_auth'
        values (if they exists)."""

    dirty_context = {
        "user": "test",
        "ignore_auth": True,
        "to_be_cleaned": "test",
    }
    dirty_Context = cast(Context, dirty_context)
    cleaned_context = logic.fresh_context(dirty_Context)

    assert "to_be_cleaned" not in cleaned_context
    assert cleaned_context["user"] == "test"
    assert cleaned_context["ignore_auth"] is True
    assert "model" not in cleaned_context
    assert "session" not in cleaned_context
    assert "auth_user_obj" not in cleaned_context


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
