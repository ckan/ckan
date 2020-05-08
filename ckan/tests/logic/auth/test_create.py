# encoding: utf-8
"""Unit tests for ckan/logic/auth/create.py.

"""

import mock
import pytest

import ckan.logic.auth.create as auth_create
import ckan.model as core_model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers

logic = helpers.logic


def test_anon_cant_create():
    response = auth_create.package_create({"user": None}, None)
    assert not response["success"]


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
def test_anon_can_create():
    response = auth_create.package_create({"user": None}, None)
    assert response["success"]


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
@pytest.mark.ckan_config(
    "ckan.auth.create_dataset_if_not_in_organization", False
)
def test_cdnio_overrides_acd():
    response = auth_create.package_create({"user": None}, None)
    assert not response["success"]


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
@pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", False)
def test_cud_overrides_acd():
    response = auth_create.package_create({"user": None}, None)
    assert not response["success"]


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestRealUsersAuth(object):
    def test_no_org_user_can_create(self):
        user = factories.User()
        response = auth_create.package_create({"user": user["name"]}, None)
        assert response["success"]

    @pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
    @pytest.mark.ckan_config(
        "ckan.auth.create_dataset_if_not_in_organization", False
    )
    def test_no_org_user_cant_create_if_cdnio_false(self):
        user = factories.User()
        response = auth_create.package_create({"user": user["name"]}, None)
        assert not response["success"]

    @pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", False)
    def test_no_org_user_cant_create_if_cud_false(self):
        user = factories.User()
        response = auth_create.package_create({"user": user["name"]}, None)
        assert not response["success"]

    def test_same_org_user_can_create(self):
        user = factories.User()
        org_users = [{"name": user["name"], "capacity": "editor"}]
        org = factories.Organization(users=org_users)
        dataset = {"name": "same-org-user-can-create", "owner_org": org["id"]}
        context = {"user": user["name"], "model": core_model}
        response = auth_create.package_create(context, dataset)
        assert response["success"]

    def test_different_org_user_cant_create(s):
        user = factories.User()
        org_users = [{"name": user["name"], "capacity": "editor"}]
        org1 = factories.Organization(users=org_users)
        org2 = factories.Organization()
        dataset = {
            "name": "different-org-user-cant-create",
            "owner_org": org2["id"],
        }
        context = {"user": user["name"], "model": core_model}
        response = auth_create.package_create(context, dataset)
        assert not response["success"]

    @mock.patch("ckan.logic.auth.create.group_member_create")
    def test_user_invite_delegates_correctly_to_group_member_create(self, gmc):
        user = factories.User()
        context = {"user": user["name"], "model": None, "auth_user_obj": user}
        data_dict = {"group_id": 42}

        gmc.return_value = {"success": False}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("user_invite", context=context, **data_dict)

        gmc.return_value = {"success": True}
        result = helpers.call_auth("user_invite", context=context, **data_dict)
        assert result

    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("with_plugins")
    def test_authorized_if_user_has_permissions_on_dataset(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        resource = factories.Resource(user=user, package_id=dataset["id"])

        resource_view = {
            "resource_id": resource["id"],
            "title": u"Resource View",
            "view_type": u"image_view",
            "image_url": "url",
        }

        context = {"user": user["name"], "model": core_model}
        response = helpers.call_auth(
            "resource_view_create", context=context, **resource_view
        )
        assert response

    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("with_plugins")
    def test_not_authorized_if_user_has_no_permissions_on_dataset(self):

        org = factories.Organization()

        user = factories.User()

        member = {"username": user["name"], "role": "admin", "id": org["id"]}
        helpers.call_action("organization_member_create", **member)

        user_2 = factories.User()

        dataset = factories.Dataset(owner_org=org["id"])

        resource = factories.Resource(package_id=dataset["id"])

        resource_view = {
            "resource_id": resource["id"],
            "title": u"Resource View",
            "view_type": u"image_view",
            "image_url": "url",
        }

        context = {"user": user_2["name"], "model": core_model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_view_create", context=context, **resource_view
            )

    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("with_plugins")
    def test_not_authorized_if_not_logged_in_3(self):

        resource_view = {
            "title": u"Resource View",
            "view_type": u"image_view",
            "image_url": "url",
        }

        context = {"user": None, "model": core_model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_view_create", context=context, **resource_view
            )

    def test_authorized_if_user_has_permissions_on_dataset_3(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        resource = factories.Resource(user=user, package_id=dataset["id"])

        context = {"user": user["name"], "model": core_model}
        response = helpers.call_auth(
            "resource_create_default_resource_views",
            context=context,
            resource=resource,
        )
        assert response

    def test_not_authorized_if_user_has_no_permissions_on_dataset_2(self):

        org = factories.Organization()

        user = factories.User()

        member = {"username": user["name"], "role": "admin", "id": org["id"]}
        helpers.call_action("organization_member_create", **member)

        user_2 = factories.User()

        dataset = factories.Dataset(owner_org=org["id"])

        resource = factories.Resource(package_id=dataset["id"])

        context = {"user": user_2["name"], "model": core_model}
        with pytest.raises(logic.NotAuthorized):

            helpers.call_auth(
                "resource_create_default_resource_views",
                context=context,
                resource=resource,
            )

    def test_not_authorized_if_not_logged_in_2(self):
        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset["id"])

        context = {"user": None, "model": core_model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_create_default_resource_views",
                context=context,
                resource=resource,
            )

    def test_authorized_if_user_has_permissions_on_dataset_2(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        context = {"user": user["name"], "model": core_model}
        response = helpers.call_auth(
            "package_create_default_resource_views",
            context=context,
            package=dataset,
        )
        assert response

    def test_not_authorized_if_user_has_no_permissions_on_dataset_3(self):

        org = factories.Organization()

        user = factories.User()

        member = {"username": user["name"], "role": "admin", "id": org["id"]}
        helpers.call_action("organization_member_create", **member)

        user_2 = factories.User()

        dataset = factories.Dataset(owner_org=org["id"])

        context = {"user": user_2["name"], "model": core_model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_create_default_resource_views",
                context=context,
                package=dataset,
            )

    def test_not_authorized_if_not_logged_in(self):
        dataset = factories.Dataset()

        context = {"user": None, "model": core_model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_create_default_resource_views",
                context=context,
                package=dataset,
            )

    def test_authorized_if_user_has_permissions_on_dataset_4(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        resource = {
            "package_id": dataset["id"],
            "title": "Resource",
            "url": "http://test",
            "format": "csv",
        }

        context = {"user": user["name"], "model": core_model}
        response = helpers.call_auth(
            "resource_create", context=context, **resource
        )
        assert response

    def test_not_authorized_if_user_has_no_permissions_on_dataset_4(self):

        org = factories.Organization()

        user = factories.User()

        member = {"username": user["name"], "role": "admin", "id": org["id"]}
        helpers.call_action("organization_member_create", **member)

        user_2 = factories.User()

        dataset = factories.Dataset(user=user, owner_org=org["id"])

        resource = {
            "package_id": dataset["id"],
            "title": "Resource",
            "url": "http://test",
            "format": "csv",
        }

        context = {"user": user_2["name"], "model": core_model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_create", context=context, **resource)

    def test_not_authorized_if_not_logged_in_4(self):

        resource = {"title": "Resource", "url": "http://test", "format": "csv"}

        context = {"user": None, "model": core_model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_create", context=context, **resource)

    def test_sysadmin_is_authorized(self):

        sysadmin = factories.Sysadmin()

        resource = {"title": "Resource", "url": "http://test", "format": "csv"}

        context = {"user": sysadmin["name"], "model": core_model}
        response = helpers.call_auth(
            "resource_create", context=context, **resource
        )
        assert response

    def test_raises_not_found_if_no_package_id_provided(self):

        user = factories.User()

        resource = {"title": "Resource", "url": "http://test", "format": "csv"}

        context = {"user": user["name"], "model": core_model}
        with pytest.raises(logic.NotFound):
            helpers.call_auth("resource_create", context=context, **resource)

    def test_raises_not_found_if_dataset_was_not_found(self):

        user = factories.User()

        resource = {
            "package_id": "does_not_exist",
            "title": "Resource",
            "url": "http://test",
            "format": "csv",
        }

        context = {"user": user["name"], "model": core_model}
        with pytest.raises(logic.NotFound):
            helpers.call_auth("resource_create", context=context, **resource)

    def test_normal_user_cant_use_it(self):
        normal_user = factories.User()
        context = {"user": normal_user["name"], "model": core_model}

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("activity_create", context=context)
