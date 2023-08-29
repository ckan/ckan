# -*- coding: utf-8 -*-

from unittest import mock
import pytest
from ckan import logic, model
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
    logic.check_access("package_create", {})
    is_authorized.assert_called_once()
    context = is_authorized.call_args[0][1]
    assert context["user"] == ""

    is_authorized.reset_mock()

    logic.check_access("package_create", {"user": "test"})
    context = is_authorized.call_args[0][1]
    assert context["user"] == "test"


def test_get_action_optional_params():

    assert "ckan_version" in logic.get_action("status_show")()


def test_fresh_context():
    """ Test the fresh_context function.
        It should return a new context object only with
        'model', 'session', 'user', 'auth_user_obj', 'ignore_auth'
        values (if they exists)."""

    dirty_context: Context = {
        "user": "test",
        "ignore_auth": True,
        "to_be_cleaned": "test",
    }

    cleaned_context = logic.fresh_context(dirty_context)

    assert "to_be_cleaned" not in cleaned_context
    assert cleaned_context["user"] == "test"
    assert cleaned_context["ignore_auth"] is True
    assert "model" not in cleaned_context
    assert "session" not in cleaned_context
    assert "auth_user_obj" not in cleaned_context


def test_check_access_auth_user_for_different_objects():
    user1 = factories.User()
    user2 = factories.User()
    context = {"user": user1["name"]}

    organization1 = factories.Organization(user=user1)
    organization2 = factories.Organization(user=user2)

    datasets1 = [
        factories.Dataset(owner_org=organization1["id"], private=True)
        for _ in range(0, 1)
    ]
    datasets2 = [
        factories.Dataset(owner_org=organization2["id"], private=True)
        for _ in range(0, 1)
    ]
    dataset3 = datasets1 + datasets2

    with pytest.raises(logic.NotAuthorized):
        for dataset in dataset3:
            logic.check_access("package_show", context, {'id': dataset["id"]})
