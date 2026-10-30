"""Tests for authorization in ckan/logic/auth/resource_view.py."""

import pytest

from ckan import model
from ckan.tests import factories, helpers

logic = helpers.logic


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestGetAuthWithCollaboratorsResourceView(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    def test_resource_view_list_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_view_list", context=context, id=resource["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="editor",
        )

        assert helpers.call_auth(
            "resource_view_list", context=context, id=resource["id"]
        )

    def test_resource_view_list_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_view_list", context=context, id=resource["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        assert helpers.call_auth(
            "resource_view_list", context=context, id=resource["id"]
        )

    def test_resource_view_show_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        resource_view = factories.ResourceView(resource_id=resource["id"])
        user = factories.User()

        context = self._get_context(user)
        # Needed until ckan/ckan#4828 is backported
        context["resource"] = model.Resource.get(resource["id"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_view_show", context=context, id=resource_view["id"]
            )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="editor",
        )

        assert helpers.call_auth(
            "resource_view_show", context=context, id=resource_view["id"]
        )

    def test_resource_view_show_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        resource_view = factories.ResourceView(resource_id=resource["id"])
        user = factories.User()

        context = self._get_context(user)
        # Needed until ckan/ckan#4828 is backported
        context["resource"] = model.Resource.get(resource["id"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_view_show", context=context, id=resource_view["id"]
            )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        assert helpers.call_auth(
            "resource_view_show", context=context, id=resource_view["id"]
        )


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_anon_can_not_update():

    resource_view = factories.ResourceView()

    params = {
        "id": resource_view["id"],
        "title": "Resource View Updated",
        "view_type": "image_view",
        "image_url": "url",
    }

    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_view_update", context=context, **params)


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_authorized_if_user_has_permissions_on_dataset():

    user = factories.User()

    dataset = factories.Dataset(user=user)

    resource = factories.Resource(user=user, package_id=dataset["id"])

    resource_view = factories.ResourceView(resource_id=resource["id"])

    params = {
        "id": resource_view["id"],
        "resource_id": resource["id"],
        "title": "Resource View Updated",
        "view_type": "image_view",
        "image_url": "url",
    }

    context = {"user": user["name"], "model": model}
    response = helpers.call_auth("resource_view_update", context=context, **params)

    assert response


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_reorder_authorized_if_user_has_permissions_on_dataset():
    """Ensure that resource_view_reorder action correctly calls
    the auth function
    """
    user = factories.User()

    dataset = factories.Dataset(user=user)

    resource = factories.Resource(user=user, package_id=dataset["id"])

    resource_view = factories.ResourceView(resource_id=resource["id"])
    resource_view2 = factories.ResourceView(resource_id=resource["id"])

    params = {
        "id": resource["id"],
        "order": [resource_view2["id"], resource_view["id"]],
    }

    context = {"user": user["name"], "model": model, "ignore_auth": False}
    response = helpers.call_action("resource_view_reorder", context=context, **params)

    assert response


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_not_authorized_if_user_has_no_permissions_on_dataset():

    org = factories.Organization()

    user = factories.User()

    member = {"username": user["name"], "role": "admin", "id": org["id"]}
    helpers.call_action("organization_member_create", **member)

    user_2 = factories.User()

    dataset = factories.Dataset(owner_org=org["id"])

    resource = factories.Resource(package_id=dataset["id"])

    resource_view = factories.ResourceView(resource_id=resource["id"])

    params = {
        "id": resource_view["id"],
        "resource_id": resource["id"],
        "title": "Resource View Updated",
        "view_type": "image_view",
        "image_url": "url",
    }

    context = {"user": user_2["name"], "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_view_update", context=context, **params)


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
@pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
class TestUpdateAuthWithCollaboratorsResourceView(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    @pytest.mark.parametrize("role", ["admin", "editor"])
    def test_resource_view_create_public_editor(self, role):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_view_create", context=context, resource_id=resource["id"]
            )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=role,
        )

        assert helpers.call_auth(
            "resource_view_create", context=context, resource_id=resource["id"]
        )

    def test_resource_view_create_public_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_view_create", context=context, resource_id=resource["id"]
            )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_view_create", context=context, resource_id=resource["id"]
            )
