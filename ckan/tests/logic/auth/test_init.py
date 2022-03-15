# encoding: utf-8

import pytest

import ckan.logic as logic
import ckan.logic.auth as logic_auth
import ckan.model as core_model
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


def _get_function(obj_type):
    _get_object_functions = {
        "package": logic_auth.get_package_object,
        "resource": logic_auth.get_resource_object,
        "user": logic_auth.get_user_object,
        "group": logic_auth.get_group_object,
    }
    return _get_object_functions[obj_type]


def _get_object_in_context(obj_type):

    if obj_type == "user":
        context = {"user_obj": "a_fake_object"}
    else:
        context = {obj_type: "a_fake_object"}

    obj = _get_function(obj_type)(context)

    assert obj == "a_fake_object"


def _get_object_id_not_found(obj_type):

    with pytest.raises(logic.NotFound):
        _get_function(obj_type)({"model": core_model}, {"id": "not_here"})


def _get_object_id_none(obj_type):

    with pytest.raises(logic.ValidationError):
        _get_function(obj_type)({"model": core_model}, {})


def test_get_package_object_in_context():
    _get_object_in_context("package")


def test_get_resource_object_in_context():
    _get_object_in_context("resource")


def test_get_user_object_in_context():
    _get_object_in_context("user")


def test_get_group_object_in_context():
    _get_object_in_context("group")


def test_get_package_object_id_not_found():
    _get_object_id_not_found("package")


def test_get_resource_object_id_not_found():
    _get_object_id_not_found("resource")


def test_get_user_object_id_not_found():
    _get_object_id_not_found("user")


def test_get_group_object_id_not_found():
    _get_object_id_not_found("group")


def test_get_package_object_id_none():
    _get_object_id_none("package")


def test_get_resource_object_id_none():
    _get_object_id_none("resource")


def test_get_user_object_id_none():
    _get_object_id_none("user")


def test_get_group_object_id_none():
    _get_object_id_none("group")


@pytest.mark.usefixtures("non_clean_db")
class TestInit(object):
    def test_get_package_object_with_id(self):

        user_name = helpers.call_action("get_site_user")["name"]
        dataset = helpers.call_action(
            "package_create",
            context={"user": user_name},
            name=factories.Dataset.stub().name,
        )
        context = {"model": core_model}
        obj = logic_auth.get_package_object(context, {"id": dataset["id"]})

        assert obj.id == dataset["id"]
        assert context["package"] == obj

    def test_get_resource_object_with_id(self):

        user_name = helpers.call_action("get_site_user")["name"]
        dataset = helpers.call_action(
            "package_create",
            context={"user": user_name},
            name=factories.Dataset.stub().name,
        )
        resource = helpers.call_action(
            "resource_create",
            context={"user": user_name},
            package_id=dataset["id"],
            url="http://foo",
        )

        context = {"model": core_model}
        obj = logic_auth.get_resource_object(context, {"id": resource["id"]})

        assert obj.id == resource["id"]
        assert context["resource"] == obj

    def test_get_user_object_with_id(self):

        user_name = helpers.call_action("get_site_user")["name"]
        stub = factories.User.stub()
        user = helpers.call_action(
            "user_create",
            context={"user": user_name},
            name=stub.name,
            email=stub.email,
            password="TestPassword1",
        )
        context = {"model": core_model}
        obj = logic_auth.get_user_object(context, {"id": user["id"]})

        assert obj.id == user["id"]
        assert context["user_obj"] == obj

    def test_get_group_object_with_id(self):

        user_name = helpers.call_action("get_site_user")["name"]
        group = helpers.call_action(
            "group_create",
            context={"user": user_name},
            name=factories.Group.stub().name,
        )
        context = {"model": core_model}
        obj = logic_auth.get_group_object(context, {"id": group["id"]})

        assert obj.id == group["id"]
        assert context["group"] == obj
