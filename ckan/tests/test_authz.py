# encoding: utf-8

import pytest
import re

from ckan import authz as auth, model, logic

from ckan.tests import factories, helpers

_check = auth.check_config_permission


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
def test_config_overrides_default():
    assert _check("anon_create_dataset") is True


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
def test_config_override_also_works_with_prefix():
    assert _check("ckan.auth.anon_create_dataset") is True


@pytest.mark.ckan_config("ckan.auth.unknown_permission", True)
def test_unknown_permission_returns_false():
    assert _check("unknown_permission") is False


def test_unknown_permission_not_in_config_returns_false():
    assert _check("unknown_permission") is False


def test_default_roles_that_cascade_to_sub_groups_is_a_list():
    assert isinstance(_check("roles_that_cascade_to_sub_groups"), list)


@pytest.mark.ckan_config(
    "ckan.auth.roles_that_cascade_to_sub_groups", ["admin", "editor"]
)
def test_roles_that_cascade_to_sub_groups_is_a_list():
    assert sorted(_check("roles_that_cascade_to_sub_groups")) == sorted(
        ["admin", "editor"]
    )


# AttributeError
# @mock.patch('flask.globals.RuntimeError')
# def test_get_user_outside_web_request_py3(mock_runtimeerror):
#     auth._get_user("example")
#     assert mock_runtimeerror.called


@pytest.mark.usefixtures("non_clean_db")
def test_get_user_returns_user_obj():
    user = factories.User()
    assert auth._get_user(user["name"]).name == user["name"]


def test_get_user_not_found():
    name = factories.User.stub().name
    assert auth._get_user(name) is None


def test_no_attributes_set_on_imported_auth_members():
    import ckan.logic.auth.get as auth_get
    logic.check_access("package_search", {})
    assert hasattr(auth_get.package_search, "auth_allow_anonymous_access")
    assert not hasattr(auth_get.config, "auth_allow_anonymous_access")


@pytest.mark.ckan_config("ckan.site_lockdown", True)
def test_site_lockdown():
    """
    When the site is in lockdown mode, only sysadmins should be able to:
        - *_create actions
        - *_updated actions
        - *_patch actions
        - *_delete actions

    NOTE: we except ValueError due to missing auth functions from
          the followee type actions.
    TODO: remove exceptions after merging followee authz
          (https://github.com/ckan/ckan/pull/9229)
    """
    sysadmin = factories.Sysadmin()
    org_admin = factories.User()
    editor = factories.User()
    member = factories.User()
    factories.Organization(users=[{
        'name': sysadmin['name'],
        'capacity': 'admin'},
        {'name': org_admin['name'],
        'capacity': 'admin'},
        {'name': editor['name'],
        'capacity': 'editor'},
        {'name': member['name'],
        'capacity': 'member'}])

    name_patterns = [
        '_create',
        '_patch',
        '_update',
        '_delete',
        '_purge',
        '_revise',
        '_clear',
        '_cancel',
        '_revoke',
        '_reorder',
        '_invite',
        '_upsert',
        '_insert',
    ]
    name_match = '.*(%s).*' % '|'.join(name_patterns)

    # org admins cannot do things
    for action_func_name, action_func in logic._actions.items():
        if getattr(action_func, 'side_effect_free', False):
            continue
        try:
            logic.check_access(action_func_name, {'user': org_admin['name']}, {})
        except ValueError:  # TODO: remove after followee auth PR merge
            continue
        except logic.NotAuthorized as e:
            assert re.match(name_match, action_func_name) is not None
            assert e.message == 'Site is in read only mode'

    # editors cannot do things
    for action_func_name, action_func in logic._actions.items():
        if getattr(action_func, 'side_effect_free', False):
            continue
        try:
            logic.check_access(action_func_name, {'user': editor['name']}, {})
        except ValueError:  # TODO: remove after followee auth PR merge
            continue
        except logic.NotAuthorized as e:
            assert re.match(name_match, action_func_name) is not None
            assert e.message == 'Site is in read only mode'

    # members cannot do things
    for action_func_name, action_func in logic._actions.items():
        if getattr(action_func, 'side_effect_free', False):
            continue
        try:
            logic.check_access(action_func_name, {'user': member['name']}, {})
        except ValueError:  # TODO: remove after followee auth PR merge
            continue
        except logic.NotAuthorized as e:
            assert re.match(name_match, action_func_name) is not None
            assert e.message == 'Site is in read only mode'

    # sysadmins can do anything still
    for action_func_name, action_func in logic._actions.items():
        if getattr(action_func, 'side_effect_free', False):
            continue
        try:
            logic.check_access(action_func_name, {'user': sysadmin['name']}, {})
        except ValueError:  # TODO: remove after followee auth PR merge
            continue

    # using ignore_auth can do anything still
    for action_func_name, action_func in logic._actions.items():
        if getattr(action_func, 'side_effect_free', False):
            continue
        try:
            logic.check_access(action_func_name, {'user': member['name'],
                                                  'ignore_auth': True}, {})
        except ValueError:  # TODO: remove after followee auth PR merge
            continue


@pytest.mark.usefixtures("non_clean_db")
class TestAuthOrgHierarchy(object):
    def test_parent_admin_auth(self):
        user = factories.User()
        parent = factories.Organization(
            users=[{"capacity": "admin", "name": user["name"]}]
        )
        child = factories.Organization()
        helpers.call_action(
            "member_create",
            id=child["id"],
            object=parent["id"],
            object_type="group",
            capacity="parent",
        )
        context = {"model": model, "user": user["name"]}
        helpers.call_auth(
            "organization_member_create", context, id=parent["id"]
        )
        helpers.call_auth(
            "organization_member_create", context, id=child["id"]
        )

        helpers.call_auth("package_create", context, owner_org=parent["id"])
        helpers.call_auth("package_create", context, owner_org=child["id"])

    def test_child_admin_auth(self):
        user = factories.User()
        parent = factories.Organization()
        child = factories.Organization(
            users=[{"capacity": "admin", "name": user["name"]}]
        )
        helpers.call_action(
            "member_create",
            id=child["id"],
            object=parent["id"],
            object_type="group",
            capacity="parent",
        )
        context = {"model": model, "user": user["name"]}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "organization_member_create", context, id=parent["id"]
            )
        helpers.call_auth(
            "organization_member_create", context, id=child["id"]
        )

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_create", context, owner_org=parent["id"]
            )
        helpers.call_auth("package_create", context, owner_org=child["id"])

    def test_parent_editor_auth(self):
        user = factories.User()
        parent = factories.Organization(
            users=[{"capacity": "editor", "name": user["name"]}]
        )
        child = factories.Organization()
        helpers.call_action(
            "member_create",
            id=child["id"],
            object=parent["id"],
            object_type="group",
            capacity="parent",
        )
        context = {"model": model, "user": user["name"]}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "organization_member_create", context, id=parent["id"]
            )
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "organization_member_create", context, id=child["id"]
            )

        helpers.call_auth("package_create", context, owner_org=parent["id"])
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("package_create", context, owner_org=child["id"])

    def test_child_editor_auth(self):
        user = factories.User()
        parent = factories.Organization()
        child = factories.Organization(
            users=[{"capacity": "editor", "name": user["name"]}]
        )
        helpers.call_action(
            "member_create",
            id=child["id"],
            object=parent["id"],
            object_type="group",
            capacity="parent",
        )
        context = {"model": model, "user": user["name"]}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "organization_member_create", context, id=parent["id"]
            )
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "organization_member_create", context, id=child["id"]
            )

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "package_create", context, owner_org=parent["id"]
            )
        helpers.call_auth("package_create", context, owner_org=child["id"])
