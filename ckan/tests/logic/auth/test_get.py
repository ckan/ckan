# encoding: utf-8
"""Unit tests for ckan/logic/auth/get.py.

"""

import pytest
from six import string_types

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.logic as logic
from ckan import model


@pytest.mark.ckan_config(u"ckan.auth.public_user_details", u"false")
def test_auth_user_list():
    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_list", context=context)


def test_authed_user_list():
    context = {"user": None, "model": model}
    assert helpers.call_auth("user_list", context=context)


def test_user_list_email_parameter():
    context = {"user": None, "model": model}
    # using the 'email' parameter is not allowed (unless sysadmin)
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_list", email="a@example.com", context=context)


@pytest.mark.usefixtures(u"clean_db", "with_request_context")
class TestGetAuth(object):

    @pytest.mark.ckan_config(u"ckan.auth.public_user_details", u"false")
    def test_auth_user_show(self):
        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        context = {"user": None, "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("user_show", context=context, id=fred["id"])

    def test_authed_user_show(self):
        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        context = {"user": None, "model": model}
        assert helpers.call_auth("user_show", context=context, id=fred["id"])

    def test_package_show__deleted_dataset_is_hidden_to_public(self):
        dataset = factories.Dataset(state="deleted")
        context = {"model": model}
        context["user"] = ""

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_show", context=context, id=dataset["name"]
            )

    def test_package_show__deleted_dataset_is_visible_to_editor(self):

        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        org = factories.Organization(users=[fred])
        dataset = factories.Dataset(owner_org=org["id"], state="deleted")
        context = {"model": model}
        context["user"] = "fred"

        ret = helpers.call_auth(
            "package_show", context=context, id=dataset["name"]
        )
        assert ret

    def test_group_show__deleted_group_is_hidden_to_public(self):
        group = factories.Group(state="deleted")
        context = {"model": model}
        context["user"] = ""

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("group_show", context=context, id=group["name"])

    def test_group_show__deleted_group_is_visible_to_its_member(self):

        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        org = factories.Group(users=[fred], state="deleted")
        context = {"model": model}
        context["user"] = "fred"

        ret = helpers.call_auth("group_show", context=context, id=org["name"])
        assert ret

    def test_group_show__deleted_org_is_visible_to_its_member(self):

        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        org = factories.Organization(users=[fred], state="deleted")
        context = {"model": model}
        context["user"] = "fred"

        ret = helpers.call_auth("group_show", context=context, id=org["name"])
        assert ret

    @pytest.mark.ckan_config(u"ckan.auth.public_user_details", u"false")
    def test_group_show__user_is_hidden_to_public(self):
        group = factories.Group()
        context = {"model": model}
        context["user"] = ""

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "group_show",
                context=context,
                id=group["name"],
                include_users=True,
            )

    def test_group_show__user_is_avail_to_public(self):
        group = factories.Group()
        context = {"model": model}
        context["user"] = ""

        assert helpers.call_auth(
            "group_show", context=context, id=group["name"]
        )

    def test_config_option_show_anon_user(self):
        """An anon user is not authorized to use config_option_show action."""
        context = {"user": None, "model": None}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("config_option_show", context=context)

    def test_config_option_show_normal_user(self):
        """A normal logged in user is not authorized to use config_option_show
            action."""
        factories.User(name="fred")
        context = {"user": "fred", "model": None}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("config_option_show", context=context)

    def test_config_option_show_sysadmin(self):
        """A sysadmin is authorized to use config_option_show action."""
        factories.Sysadmin(name="fred")
        context = {"user": "fred", "model": None}
        assert helpers.call_auth("config_option_show", context=context)

    def test_config_option_list_anon_user(self):
        """An anon user is not authorized to use config_option_list action."""
        context = {"user": None, "model": None}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("config_option_list", context=context)

    def test_config_option_list_normal_user(self):
        """A normal logged in user is not authorized to use config_option_list
            action."""
        factories.User(name="fred")
        context = {"user": "fred", "model": None}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("config_option_list", context=context)

    def test_config_option_list_sysadmin(self):
        """A sysadmin is authorized to use config_option_list action."""
        factories.Sysadmin(name="fred")
        context = {"user": "fred", "model": None}
        assert helpers.call_auth("config_option_list", context=context)

    @pytest.mark.ckan_config(
        u"ckan.auth.public_activity_stream_detail", u"false"
    )
    def test_config_option_public_activity_stream_detail_denied(self):
        """Config option says an anon user is not authorized to get activity
            stream data/detail.
            """
        dataset = factories.Dataset()
        context = {"user": None, "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_activity_list",
                context=context,
                id=dataset["id"],
                include_data=True,
            )

    @pytest.mark.ckan_config(
        u"ckan.auth.public_activity_stream_detail", u"true"
    )
    def test_config_option_public_activity_stream_detail(self):
        """Config option says an anon user is authorized to get activity
            stream data/detail.
            """
        dataset = factories.Dataset()
        context = {"user": None, "model": model}
        helpers.call_auth(
            "package_activity_list",
            context=context,
            id=dataset["id"],
            include_data=True,
        )


@pytest.mark.usefixtures(u"clean_db")
class TestApiToken(object):
    def test_anon_is_not_allowed_to_get_tokens(self):
        user = factories.User()
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u"api_token_list",
                {u"user": None, u"model": model},
                user=user['name']
            )

    def test_auth_user_is_allowed_to_list_tokens(self):
        user = factories.User()
        helpers.call_auth(u"api_token_list", {
            u"model": model,
            u"user": user[u"name"]
        }, user=user[u"name"])


@pytest.mark.usefixtures('clean_db', 'with_plugins')
@pytest.mark.ckan_config('ckan.plugins', 'image_view')
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
class TestGetAuthWithCollaborators(object):

    def _get_context(self, user):

        return {
            'model': model,
            'user': user if isinstance(user, string_types) else user.get('name')
        }

    def test_dataset_show_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_show',
                context=context, id=dataset['id'])

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'package_show',
            context=context, id=dataset['id'])

    def test_dataset_show_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_show',
                context=context, id=dataset['id'])

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        assert helpers.call_auth(
            'package_show',
            context=context, id=dataset['id'])

    def test_resource_show_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'resource_show',
                context=context, id=resource['id'])

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'resource_show',
            context=context, id=resource['id'])

    def test_resource_show_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'resource_show',
                context=context, id=resource['id'])

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        assert helpers.call_auth(
            'resource_show',
            context=context, id=resource['id'])

    def test_resource_view_list_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'resource_view_list',
                context=context, id=resource['id'])

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'resource_view_list',
            context=context, id=resource['id'])

    def test_resource_view_list_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'resource_view_list',
                context=context, id=resource['id'])

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        assert helpers.call_auth(
            'resource_view_list',
            context=context, id=resource['id'])

    def test_resource_view_show_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        resource_view = factories.ResourceView(resource_id=resource['id'])
        user = factories.User()

        context = self._get_context(user)
        # Needed until ckan/ckan#4828 is backported
        context['resource'] = model.Resource.get(resource['id'])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'resource_view_show',
                context=context, id=resource_view['id'])

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'resource_view_show',
            context=context, id=resource_view['id'])

    def test_resource_view_show_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        resource_view = factories.ResourceView(resource_id=resource['id'])
        user = factories.User()

        context = self._get_context(user)
        # Needed until ckan/ckan#4828 is backported
        context['resource'] = model.Resource.get(resource['id'])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'resource_view_show',
                context=context, id=resource_view['id'])

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        assert helpers.call_auth(
            'resource_view_show',
            context=context, id=resource_view['id'])


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberList(object):

    def _get_context(self, user):

        return {
            'model': model,
            'user': user if isinstance(user, string_types) else user.get('name')
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

    def test_list_org_admin_is_authorized(self):

        context = self._get_context(self.org_admin)
        assert helpers.call_auth(
            'package_collaborator_list',
            context=context, id=self.dataset['id'])

    def test_list_org_editor_is_not_authorized(self):

        context = self._get_context(self.org_editor)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_list',
                context=context, id=self.dataset['id'])

    def test_list_org_member_is_not_authorized(self):

        context = self._get_context(self.org_member)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_list',
                context=context, id=self.dataset['id'])

    def test_list_org_admin_from_other_org_is_not_authorized(self):
        org_admin2 = factories.User()
        factories.Organization(
            users=[
                {'name': org_admin2['name'], 'capacity': 'admin'},
            ]
        )

        context = self._get_context(org_admin2)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_list_for_user',
                context=context, id=self.dataset['id'])

    @pytest.mark.ckan_config('ckan.auth.allow_admin_collaborators', True)
    def test_list_collaborator_admin_is_authorized(self):

        user = factories.User()

        helpers.call_action(
            'package_collaborator_create',
            id=self.dataset['id'], user_id=user['id'], capacity='admin')

        context = self._get_context(user)
        assert helpers.call_auth(
            'package_collaborator_list', context=context, id=self.dataset['id'])

    @pytest.mark.parametrize('role', ['editor', 'member'])
    def test_list_collaborator_editor_and_member_are_not_authorized(self, role):
        user = factories.User()

        helpers.call_action(
            'package_collaborator_create',
            id=self.dataset['id'], user_id=user['id'], capacity=role)

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_list',
                context=context, id=self.dataset['id'])

    def test_user_list_own_user_is_authorized(self):

        context = self._get_context(self.normal_user)
        assert helpers.call_auth(
            'package_collaborator_list_for_user',
            context=context, id=self.normal_user['id'])

    def test_user_list_org_admin_is_not_authorized(self):

        context = self._get_context(self.org_admin)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_list_for_user',
                context=context, id=self.normal_user['id'])

    def test_user_list_org_editor_is_not_authorized(self):

        context = self._get_context(self.org_editor)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_list_for_user',
                context=context, id=self.normal_user['id'])

    def test_user_list_org_member_is_not_authorized(self):

        context = self._get_context(self.org_member)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_list_for_user',
                context=context, id=self.normal_user['id'])

    def test_user_list_org_admin_from_other_org_is_not_authorized(self):
        org_admin2 = factories.User()
        factories.Organization(
            users=[
                {'name': org_admin2['name'], 'capacity': 'admin'},
            ]
        )

        context = self._get_context(org_admin2)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'package_collaborator_list_for_user',
                context=context, id=self.normal_user['id'])

    @pytest.mark.ckan_config('ckan.auth.create_dataset_if_not_in_organization', True)
    @pytest.mark.ckan_config('ckan.auth.create_unowned_dataset', True)
    def test_list_unowned_datasets(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        assert dataset['owner_org'] is None
        assert dataset['creator_user_id'] == user['id']

        context = self._get_context(user)
        assert helpers.call_auth(
            'package_collaborator_list', context=context, id=dataset['id'])
