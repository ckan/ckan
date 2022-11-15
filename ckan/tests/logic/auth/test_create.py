# encoding: utf-8
"""Unit tests for ckan/logic/auth/create.py.

"""

import unittest.mock as mock
import pytest


import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers

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
@pytest.mark.ckan_config(
    "ckan.auth.create_dataset_if_not_in_organization", False
)
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
class TestUserCreate:
    def test_sysadmin_can_create_via_api(self):
        sysadmin = factories.Sysadmin()
        context = {"user": sysadmin["name"], "model": model, "api_version": 3}
        assert helpers.call_auth("user_create", context)

    def test_anon_can_not_create_via_web(self):
        context = {"user": None, "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("user_create", context)

    def test_anon_cannot_create_via_api(self):
        context = {"user": None, "model": model, "api_version": 3}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("user_create", context)

    @pytest.mark.ckan_config("ckan.auth.create_user_via_web", False)
    def test_anon_cannot_create_via_forbidden_web(self):
        context = {"user": None, "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("user_create", context)

    @pytest.mark.ckan_config("ckan.auth.create_user_via_api", True)
    def test_anon_not_create_via_allowed_api(self):
        context = {"user": None, "model": model, "api_version": 3}
        assert helpers.call_auth("user_create", context)


@pytest.mark.usefixtures("non_clean_db")
class TestRealUsersAuth(object):
    def test_no_org_user_can_create(self):
        user = factories.User()
        context = {"user": user["name"], "model": model}
        assert helpers.call_auth("package_create", context)

    @pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
    @pytest.mark.ckan_config(
        "ckan.auth.create_dataset_if_not_in_organization", False
    )
    def test_no_org_user_cant_create_if_cdnio_false(self):
        user = factories.User()
        context = {"user": user["name"], "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("package_create", context)

    @pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", False)
    def test_no_org_user_cant_create_if_cud_false(self):
        user = factories.User()
        context = {"user": user["name"], "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("package_create", context)

    def test_same_org_user_can_create(self):
        user = factories.User()
        org_users = [{"name": user["name"], "capacity": "editor"}]
        org = factories.Organization(users=org_users)
        dataset = {"name": "same-org-user-can-create", "owner_org": org["id"]}
        context = {"user": user["name"], "model": model}
        assert helpers.call_auth("package_create", context, **dataset)

    def test_different_org_user_cant_create(self):
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

    @mock.patch("ckan.logic.auth.create.group_member_create")
    def test_user_invite_delegates_correctly_to_group_member_create(self, gmc):
        user = factories.User()
        context = {"user": user["name"], "model": None, "auth_user_obj": user}
        data_dict = {"group_id": 42}

        gmc.return_value = {"success": False}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("user_invite", context=context, **data_dict)

        gmc.return_value = {"success": True}
        assert helpers.call_auth("user_invite", context=context, **data_dict)

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

        context = {"user": user["name"], "model": model}
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

        context = {"user": user_2["name"], "model": model}
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

        context = {"user": None, "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_view_create", context=context, **resource_view
            )

    def test_authorized_if_user_has_permissions_on_dataset_3(self):

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

    def test_not_authorized_if_user_has_no_permissions_on_dataset_2(self):

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

    def test_not_authorized_if_not_logged_in_2(self):
        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset["id"])

        context = {"user": None, "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "resource_create_default_resource_views",
                context=context,
                resource=resource,
            )

    def test_authorized_if_user_has_permissions_on_dataset_2(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        context = {"user": user["name"], "model": model}
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

        context = {"user": user_2["name"], "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_create_default_resource_views",
                context=context,
                package=dataset,
            )

    def test_not_authorized_if_not_logged_in(self):
        dataset = factories.Dataset()

        context = {"user": None, "model": model}
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

        context = {"user": user["name"], "model": model}
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

        context = {"user": user_2["name"], "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_create", context=context, **resource)

    def test_not_authorized_if_not_logged_in_4(self):

        resource = {"title": "Resource", "url": "http://test", "format": "csv"}

        context = {"user": None, "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("resource_create", context=context, **resource)

    def test_sysadmin_is_authorized(self):

        sysadmin = factories.Sysadmin()

        resource = {"title": "Resource", "url": "http://test", "format": "csv"}

        context = {"user": sysadmin["name"], "model": model}
        response = helpers.call_auth(
            "resource_create", context=context, **resource
        )
        assert response

    def test_raises_not_found_if_no_package_id_provided(self):

        user = factories.User()

        resource = {"title": "Resource", "url": "http://test", "format": "csv"}

        context = {"user": user["name"], "model": model}
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

        context = {"user": user["name"], "model": model}
        with pytest.raises(logic.NotFound):
            helpers.call_auth("resource_create", context=context, **resource)


class TestApiToken(object):
    def test_anon_is_not_allowed_to_create_tokens(self):
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u"api_token_create", {u"user": None, u"model": model}
            )

    @pytest.mark.usefixtures(u"non_clean_db")
    def test_auth_user_is_allowed_to_create_tokens(self):
        user = factories.User()
        helpers.call_auth(
            u"api_token_create",
            {u"model": model, u"user": user[u"name"]},
            user=user[u"name"],
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberCreateAuth(object):
    def _get_context(self, user):

        return {
            "model": model,
            "user": user if isinstance(user, str) else user.get("name"),
        }

    def setup(self):

        self.org_admin = factories.User()
        self.org_editor = factories.User()
        self.org_member = factories.User()

        self.normal_user = factories.User()

        self.org = factories.Organization(
            users=[
                {'name': self.org_admin['name'], 'capacity': 'admin'},
                {'name': self.org_editor['name'], 'capacity': 'editor'},
                {'name': self.org_member['name'], 'capacity': 'member'},
            ]
        )

        self.dataset = factories.Dataset(owner_org=self.org['id'])

    def test_create_org_admin_is_authorized(self):

        context = self._get_context(self.org_admin)
        assert helpers.call_auth(
            'package_collaborator_create', context=context, id=self.dataset['id'])

    def test_create_org_editor_is_not_authorized(self):

        context = self._get_context(self.org_editor)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_create',
                context=context, id=self.dataset['id'])

    def test_create_org_member_is_not_authorized(self):

        context = self._get_context(self.org_member)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_create',
                context=context, id=self.dataset['id'])

    def test_create_non_org_user_is_not_authorized(self):

        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_create',
                context=context, id=self.dataset['id'])

    def test_create_org_admin_from_other_org_is_not_authorized(self):

        org_admin2 = factories.User()
        factories.Organization(
            users=[
                {'name': org_admin2['name'], 'capacity': 'admin'},
            ]
        )

        context = self._get_context(org_admin2)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_create',
                context=context, id=self.dataset['id'])

    def test_create_missing_org_is_not_authorized(self):

        dataset = factories.Dataset(owner_org=None)

        context = self._get_context(self.org_admin)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_create',
                context=context, id=dataset['id'])

    @pytest.mark.ckan_config('ckan.auth.allow_admin_collaborators', True)
    def test_create_collaborator_admin_is_authorized(self):

        user = factories.User()

        helpers.call_action(
            'package_collaborator_create',
            id=self.dataset['id'], user_id=user['id'], capacity='admin')

        context = self._get_context(user)
        assert helpers.call_auth(
            'package_collaborator_create', context=context, id=self.dataset['id'])

    @pytest.mark.parametrize('role', ['editor', 'member'])
    def test_create_collaborator_editor_and_member_are_not_authorized(self, role):
        user = factories.User()

        helpers.call_action(
            'package_collaborator_create',
            id=self.dataset['id'], user_id=user['id'], capacity=role)

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_create',
                context=context, id=self.dataset['id'])

    @pytest.mark.ckan_config('ckan.auth.create_dataset_if_not_in_organization', True)
    @pytest.mark.ckan_config('ckan.auth.create_unowned_dataset', True)
    def test_create_unowned_datasets(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        assert dataset['owner_org'] is None
        assert dataset['creator_user_id'] == user['id']

        context = self._get_context(user)
        assert helpers.call_auth(
            'package_collaborator_create', context=context, id=dataset['id'])
