"""Tests for authorization in ckan/logic/auth/package.py."""

import pytest

from ckan import model
from ckan.tests import factories, helpers

logic = helpers.logic


def test_anon_cant_create():
    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("package_create", context)


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
def test_anon_can_create():
    context = {"user": None, "model": model}
    assert helpers.call_auth("package_create", context)


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
@pytest.mark.ckan_config("ckan.auth.create_dataset_if_not_in_organization", False)
def test_cdnio_overrides_acd():
    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("package_create", context)


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
@pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", False)
def test_cud_overrides_acd():
    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("package_create", context)


@pytest.mark.usefixtures("non_clean_db")
def test_no_org_user_can_create():
    user = factories.User()
    context = {"user": user["name"], "model": model}
    assert helpers.call_auth("package_create", context)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
@pytest.mark.ckan_config("ckan.auth.create_dataset_if_not_in_organization", False)
def test_no_org_user_cant_create_if_cdnio_false():
    user = factories.User()
    context = {"user": user["name"], "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("package_create", context)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
@pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", False)
def test_no_org_user_cant_create_if_cud_false():
    user = factories.User()
    context = {"user": user["name"], "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("package_create", context)


@pytest.mark.usefixtures("non_clean_db")
def test_same_org_user_can_create():
    user = factories.User()
    org_users = [{"name": user["name"], "capacity": "editor"}]
    org = factories.Organization(users=org_users)
    dataset = {"name": "same-org-user-can-create", "owner_org": org["id"]}
    context = {"user": user["name"], "model": model}
    assert helpers.call_auth("package_create", context, **dataset)


@pytest.mark.usefixtures("non_clean_db")
def test_different_org_user_cant_create():
    user = factories.User()
    org_users = [{"name": user["name"], "capacity": "editor"}]
    factories.Organization(users=org_users)
    org2 = factories.Organization()
    dataset = {
        "name": "different-org-user-cant-create",
        "owner_org": org2["id"],
    }
    context = {"user": user["name"], "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("package_create", context, **dataset)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_authorized_if_user_has_permissions_on_dataset():

    user = factories.User()

    dataset = factories.Dataset(user=user)

    resource = factories.Resource(user=user, package_id=dataset["id"])

    resource_view = {
        "resource_id": resource["id"],
        "title": "Resource View",
        "view_type": "image_view",
        "image_url": "url",
    }

    context = {"user": user["name"], "model": model}
    response = helpers.call_auth(
        "resource_view_create", context=context, **resource_view
    )
    assert response


@pytest.mark.usefixtures("non_clean_db")
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

    resource_view = {
        "resource_id": resource["id"],
        "title": "Resource View",
        "view_type": "image_view",
        "image_url": "url",
    }

    context = {"user": user_2["name"], "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_view_create", context=context, **resource_view)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_not_authorized_if_not_logged_in_3():

    resource_view = {
        "title": "Resource View",
        "view_type": "image_view",
        "image_url": "url",
    }

    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_view_create", context=context, **resource_view)


@pytest.mark.usefixtures("non_clean_db")
def test_authorized_if_user_has_permissions_on_dataset_3():

    user = factories.User()

    dataset = factories.Dataset(user=user)

    resource = factories.Resource(user=user, package_id=dataset["id"])

    context = {"user": user["name"], "model": model}
    response = helpers.call_auth(
        "resource_create_default_resource_views",
        context=context,
        resource=resource,
    )
    assert response


@pytest.mark.usefixtures("non_clean_db")
def test_not_authorized_if_user_has_no_permissions_on_dataset_2():

    org = factories.Organization()

    user = factories.User()

    member = {"username": user["name"], "role": "admin", "id": org["id"]}
    helpers.call_action("organization_member_create", **member)

    user_2 = factories.User()

    dataset = factories.Dataset(owner_org=org["id"])

    resource = factories.Resource(package_id=dataset["id"])

    context = {"user": user_2["name"], "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "resource_create_default_resource_views",
            context=context,
            resource=resource,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_not_authorized_if_not_logged_in_2():
    dataset = factories.Dataset()

    resource = factories.Resource(package_id=dataset["id"])

    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "resource_create_default_resource_views",
            context=context,
            resource=resource,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_authorized_if_user_has_permissions_on_dataset_2():

    user = factories.User()

    dataset = factories.Dataset(user=user)

    context = {"user": user["name"], "model": model}
    response = helpers.call_auth(
        "package_create_default_resource_views",
        context=context,
        package=dataset,
    )
    assert response


@pytest.mark.usefixtures("non_clean_db")
def test_not_authorized_if_user_has_no_permissions_on_dataset_3():

    org = factories.Organization()

    user = factories.User()

    member = {"username": user["name"], "role": "admin", "id": org["id"]}
    helpers.call_action("organization_member_create", **member)

    user_2 = factories.User()

    dataset = factories.Dataset(owner_org=org["id"])

    context = {"user": user_2["name"], "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "package_create_default_resource_views",
            context=context,
            package=dataset,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_not_authorized_if_not_logged_in():
    dataset = factories.Dataset()

    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "package_create_default_resource_views",
            context=context,
            package=dataset,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_authorized_if_user_has_permissions_on_dataset_4():

    user = factories.User()

    dataset = factories.Dataset(user=user)

    resource = {
        "package_id": dataset["id"],
        "title": "Resource",
        "url": "http://test",
        "format": "csv",
    }

    context = {"user": user["name"], "model": model}
    response = helpers.call_auth("resource_create", context=context, **resource)
    assert response


@pytest.mark.usefixtures("non_clean_db")
def test_not_authorized_if_user_has_no_permissions_on_dataset_4():

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

    context = {"user": user_2["name"], "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_create", context=context, **resource)


@pytest.mark.usefixtures("non_clean_db")
def test_not_authorized_if_not_logged_in_4():

    resource = {"title": "Resource", "url": "http://test", "format": "csv"}

    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_create", context=context, **resource)


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_is_authorized():

    sysadmin = factories.Sysadmin()

    resource = {"title": "Resource", "url": "http://test", "format": "csv"}

    context = {"user": sysadmin["name"], "model": model}
    response = helpers.call_auth("resource_create", context=context, **resource)
    assert response


@pytest.mark.usefixtures("non_clean_db")
def test_raises_not_found_if_no_package_id_provided():

    user = factories.User()

    resource = {"title": "Resource", "url": "http://test", "format": "csv"}

    context = {"user": user["name"], "model": model}
    with pytest.raises(logic.NotFound):
        helpers.call_auth("resource_create", context=context, **resource)


@pytest.mark.usefixtures("non_clean_db")
def test_raises_not_found_if_dataset_was_not_found():

    user = factories.User()

    resource = {
        "package_id": "does_not_exist",
        "title": "Resource",
        "url": "http://test",
        "format": "csv",
    }

    context = {"user": user["name"], "model": model}
    with pytest.raises(logic.NotFound):
        helpers.call_auth("resource_create", context=context, **resource)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberCreateAuth(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    def test_create_org_admin_is_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_admin"])
        assert helpers.call_auth(
            "package_collaborator_create",
            context=context,
            id=members_fixtures["dataset"]["id"],
        )

    def test_create_org_editor_is_not_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_editor"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_create",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    def test_create_org_member_is_not_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_member"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_create",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    def test_create_non_org_user_is_not_authorized(self, members_fixtures):

        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_create",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    def test_create_org_admin_from_other_org_is_not_authorized(self, members_fixtures):

        org_admin2 = factories.User()
        factories.Organization(
            users=[
                {"name": org_admin2["name"], "capacity": "admin"},
            ]
        )

        context = self._get_context(org_admin2)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_create",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    def test_create_missing_org_is_not_authorized(self, members_fixtures):

        dataset = factories.Dataset(owner_org=None)

        context = self._get_context(members_fixtures["org_admin"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_create", context=context, id=dataset["id"]
            )

    @pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
    def test_create_collaborator_admin_is_authorized(self, members_fixtures):

        user = factories.User()

        helpers.call_action(
            "package_collaborator_create",
            id=members_fixtures["dataset"]["id"],
            user_id=user["id"],
            capacity="admin",
        )

        context = self._get_context(user)
        assert helpers.call_auth(
            "package_collaborator_create",
            context=context,
            id=members_fixtures["dataset"]["id"],
        )

    @pytest.mark.parametrize("role", ["editor", "member"])
    def test_create_collaborator_editor_and_member_are_not_authorized(
        self, role, members_fixtures
    ):
        user = factories.User()

        helpers.call_action(
            "package_collaborator_create",
            id=members_fixtures["dataset"]["id"],
            user_id=user["id"],
            capacity=role,
        )

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_create",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    @pytest.mark.ckan_config("ckan.auth.create_dataset_if_not_in_organization", True)
    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", True)
    def test_create_unowned_datasets(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        assert dataset["owner_org"] is None
        assert dataset["creator_user_id"] == user["id"]

        context = self._get_context(user)
        assert helpers.call_auth(
            "package_collaborator_create", context=context, id=dataset["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberDeleteAuth(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    @pytest.fixture(autouse=True)
    def setup(self, clean_db):

        self.org_admin = factories.User()
        self.org_editor = factories.User()
        self.org_member = factories.User()

        self.normal_user = factories.User()

        self.org = factories.Organization(
            users=[
                {"name": self.org_admin["name"], "capacity": "admin"},
                {"name": self.org_editor["name"], "capacity": "editor"},
                {"name": self.org_member["name"], "capacity": "member"},
            ]
        )

        self.dataset = factories.Dataset(owner_org=self.org["id"])

    def test_delete_org_admin_is_authorized(self):

        context = self._get_context(self.org_admin)
        assert helpers.call_auth(
            "package_collaborator_delete", context=context, id=self.dataset["id"]
        )

    def test_delete_org_editor_is_not_authorized(self):

        context = self._get_context(self.org_editor)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_delete", context=context, id=self.dataset["id"]
            )

    def test_delete_org_member_is_not_authorized(self):

        context = self._get_context(self.org_member)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_delete", context=context, id=self.dataset["id"]
            )

    def test_delete_org_admin_from_other_org_is_not_authorized(self):
        org_admin2 = factories.User()
        factories.Organization(
            users=[
                {"name": org_admin2["name"], "capacity": "admin"},
            ]
        )

        context = self._get_context(org_admin2)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_delete", context=context, id=self.dataset["id"]
            )

    def test_delete_missing_org_is_not_authorized(self):

        dataset = factories.Dataset(owner_org=None)

        context = self._get_context(self.org_admin)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_delete", context=context, id=dataset["id"]
            )

    @pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
    def test_delete_collaborator_admin_is_authorized(self):

        user = factories.User()

        helpers.call_action(
            "package_collaborator_create",
            id=self.dataset["id"],
            user_id=user["id"],
            capacity="admin",
        )

        context = self._get_context(user)
        assert helpers.call_auth(
            "package_collaborator_delete", context=context, id=self.dataset["id"]
        )

    @pytest.mark.parametrize("role", ["editor", "member"])
    def test_delete_collaborator_editor_and_member_are_not_authorized(self, role):
        user = factories.User()

        helpers.call_action(
            "package_collaborator_create",
            id=self.dataset["id"],
            user_id=user["id"],
            capacity=role,
        )

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_delete", context=context, id=self.dataset["id"]
            )

    @pytest.mark.ckan_config("ckan.auth.create_dataset_if_not_in_organization", True)
    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", True)
    def test_delete_unowned_datasets(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        assert dataset["owner_org"] is None
        assert dataset["creator_user_id"] == user["id"]

        context = self._get_context(user)
        assert helpers.call_auth(
            "package_collaborator_delete", context=context, id=dataset["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
def test_package_show__deleted_dataset_is_hidden_to_public():
    dataset = factories.Dataset(state="deleted")
    context = {"model": model}
    context["user"] = ""

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("package_show", context=context, id=dataset["name"])


@pytest.mark.usefixtures("non_clean_db")
def test_package_show__deleted_dataset_is_visible_to_editor():

    fred = factories.User()
    fred["capacity"] = "editor"
    org = factories.Organization(users=[fred])
    dataset = factories.Dataset(owner_org=org["id"], state="deleted")
    context = {"model": model}
    context["user"] = fred["name"]

    ret = helpers.call_auth("package_show", context=context, id=dataset["name"])
    assert ret


@pytest.mark.usefixtures("non_clean_db", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestGetAuthWithCollaboratorsPackage(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    def test_dataset_show_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("package_show", context=context, id=dataset["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="editor",
        )

        assert helpers.call_auth("package_show", context=context, id=dataset["id"])

    def test_dataset_show_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org["id"])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("package_show", context=context, id=dataset["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        assert helpers.call_auth("package_show", context=context, id=dataset["id"])


@pytest.fixture
def members_fixtures():
    org_admin = factories.User()
    org_editor = factories.User()
    org_member = factories.User()

    normal_user = factories.User()

    org = factories.Organization(
        users=[
            {"name": org_admin["name"], "capacity": "admin"},
            {"name": org_editor["name"], "capacity": "editor"},
            {"name": org_member["name"], "capacity": "member"},
        ]
    )

    dataset = factories.Dataset(owner_org=org["id"])

    return locals()


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberList(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    def test_list_org_admin_is_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_admin"])
        assert helpers.call_auth(
            "package_collaborator_list",
            context=context,
            id=members_fixtures["dataset"]["id"],
        )

    def test_list_org_editor_is_not_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_editor"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_list",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    def test_list_org_member_is_not_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_member"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_list",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    def test_list_org_admin_from_other_org_is_not_authorized(self, members_fixtures):
        org_admin2 = factories.User()
        factories.Organization(
            users=[
                {"name": org_admin2["name"], "capacity": "admin"},
            ]
        )

        context = self._get_context(org_admin2)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_list_for_user",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    @pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
    def test_list_collaborator_admin_is_authorized(self, members_fixtures):

        user = factories.User()

        helpers.call_action(
            "package_collaborator_create",
            id=members_fixtures["dataset"]["id"],
            user_id=user["id"],
            capacity="admin",
        )

        context = self._get_context(user)
        assert helpers.call_auth(
            "package_collaborator_list",
            context=context,
            id=members_fixtures["dataset"]["id"],
        )

    @pytest.mark.parametrize("role", ["editor", "member"])
    def test_list_collaborator_editor_and_member_are_not_authorized(
        self, role, members_fixtures
    ):
        user = factories.User()

        helpers.call_action(
            "package_collaborator_create",
            id=members_fixtures["dataset"]["id"],
            user_id=user["id"],
            capacity=role,
        )

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_list",
                context=context,
                id=members_fixtures["dataset"]["id"],
            )

    def test_user_list_own_user_is_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["normal_user"])
        assert helpers.call_auth(
            "package_collaborator_list_for_user",
            context=context,
            id=members_fixtures["normal_user"]["id"],
        )

    def test_user_list_org_admin_is_not_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_admin"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_list_for_user",
                context=context,
                id=members_fixtures["normal_user"]["id"],
            )

    def test_user_list_org_editor_is_not_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_editor"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_list_for_user",
                context=context,
                id=members_fixtures["normal_user"]["id"],
            )

    def test_user_list_org_member_is_not_authorized(self, members_fixtures):

        context = self._get_context(members_fixtures["org_member"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_list_for_user",
                context=context,
                id=members_fixtures["normal_user"]["id"],
            )

    def test_user_list_org_admin_from_other_org_is_not_authorized(
        self, members_fixtures
    ):
        org_admin2 = factories.User()
        factories.Organization(
            users=[
                {"name": org_admin2["name"], "capacity": "admin"},
            ]
        )

        context = self._get_context(org_admin2)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_collaborator_list_for_user",
                context=context,
                id=members_fixtures["normal_user"]["id"],
            )

    @pytest.mark.ckan_config("ckan.auth.create_dataset_if_not_in_organization", True)
    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", True)
    def test_list_unowned_datasets(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        assert dataset["owner_org"] is None
        assert dataset["creator_user_id"] == user["id"]

        context = self._get_context(user)
        assert helpers.call_auth(
            "package_collaborator_list", context=context, id=dataset["id"]
        )


@pytest.mark.usefixtures("non_clean_db", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
@pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
class TestUpdateAuthWithCollaboratorsPackage(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    @pytest.mark.parametrize(
        "role,action,private",
        [
            ("admin", "package_update", False),
            ("editor", "package_update", False),
            ("admin", "package_update", True),
            ("editor", "package_update", True),
            ("admin", "package_delete", False),
            ("editor", "package_delete", False),
            ("admin", "package_delete", True),
            ("editor", "package_delete", True),
        ],
    )
    def test_dataset_manage_admin_and_editors(self, role, action, private):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"], private=private)
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(action, context=context, id=dataset["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=role,
        )

        assert helpers.call_auth(action, context=context, id=dataset["id"])

    @pytest.mark.parametrize(
        "action,private",
        [
            ("package_update", False),
            ("package_update", False),
            ("package_update", True),
            ("package_update", True),
            ("package_reindex", False),
            ("package_reindex", True),
            ("package_delete", False),
            ("package_delete", False),
            ("package_delete", True),
            ("package_delete", True),
        ],
    )
    def test_dataset_manage_member(self, action, private):

        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"], private=private)
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(action, context=context, id=dataset["id"])

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(action, context=context, id=dataset["id"])
