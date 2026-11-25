"""Tests for authorization in ckan/logic/auth/resource.py."""

import pytest

from ckan import model
from ckan.tests import factories, helpers

logic = helpers.logic


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestGetAuthWithCollaboratorsResource(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    def test_resource_show_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_show", context=context, id=resource["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="editor",
        )

        assert helpers.call_auth("resource_show", context=context, id=resource["id"])

    def test_resource_show_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_show", context=context, id=resource["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        assert helpers.call_auth("resource_show", context=context, id=resource["id"])


@pytest.mark.parametrize("func", ["resource_search"])
def test_anonymous_can_call_get_method(func):
    user = factories.User()
    context = {"user": "", "model": model}
    assert helpers.call_auth(func, context, id=user["id"])


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
@pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
class TestUpdateAuthWithCollaboratorsResource(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    @pytest.mark.parametrize("role", ["admin", "editor"])
    def test_resource_create_public_admin_and_editor(self, role):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_create", context=context, package_id=dataset["id"]
            )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=role,
        )

        assert helpers.call_auth(
            "resource_create", context=context, package_id=dataset["id"]
        )

    def test_resource_create_public_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_create", context=context, package_id=dataset["id"]
            )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_create", context=context, package_id=dataset["id"]
            )

    @pytest.mark.parametrize(
        "role,action",
        [
            ("admin", "resource_update"),
            ("editor", "resource_update"),
            ("admin", "resource_delete"),
            ("editor", "resource_delete"),
        ],
    )
    def test_resource_manage_public_admin_and_editor(self, role, action):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(action, context=context, id=resource["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=role,
        )

        assert helpers.call_auth(action, context=context, id=resource["id"])

    def test_resource_update_public_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_update", context=context, id=resource["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_update", context=context, id=resource["id"])

    def test_resource_delete_public_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_delete", context=context, id=resource["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_delete", context=context, id=resource["id"])
