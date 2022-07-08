# -*- coding: utf-8 -*-

from unittest import mock
import pytest
from ckan import logic, model
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
