"""Tests for authorization in ckan/logic/auth/user.py."""

import unittest.mock as mock
import pytest
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.logic.auth.resource as auth_resource


from ckan import authz

logic = helpers.logic


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_can_create_via_api():
    sysadmin = factories.Sysadmin()
    context = {"user": sysadmin["name"], "model": model, "api_version": 3}
    assert helpers.call_auth("user_create", context)


@pytest.mark.usefixtures("non_clean_db")
def test_anon_can_not_create_via_web():
    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_create", context)


@pytest.mark.usefixtures("non_clean_db")
def test_anon_cannot_create_via_api():
    context = {"user": None, "model": model, "api_version": 3}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_create", context)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", False)
def test_anon_cannot_create_via_forbidden_web():
    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_create", context)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_api", True)
def test_anon_not_create_via_allowed_api():
    context = {"user": None, "model": model, "api_version": 3}
    assert helpers.call_auth("user_create", context)


@pytest.mark.usefixtures("non_clean_db")
@mock.patch("ckan.logic.auth.group._group_or_org_member_create")
def test_user_invite_delegates_correctly_to_group_member_create(gmc):
    user = factories.User()
    context = {"user": user["name"], "model": None, "auth_user_obj": user}
    data_dict = {"group_id": 42}

    gmc.return_value = {"success": False}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_invite", context=context, **data_dict)

    gmc.return_value = {"success": True}
    assert helpers.call_auth("user_invite", context=context, **data_dict)


def test_anon_is_not_allowed_to_create_tokens():
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("api_token_create", {"user": None, "model": model})


@pytest.mark.usefixtures("non_clean_db")
def test_auth_user_is_allowed_to_create_tokens():
    user = factories.User()
    helpers.call_auth(
        "api_token_create",
        {"model": model, "user": user["name"]},
        user=user["name"],
    )


@pytest.mark.usefixtures("non_clean_db")
def test_auth_deleted_users_are_always_unauthorized():
    def always_success(x, y):
        return {"success": True}

    authz._AuthFunctions._build()
    authz._AuthFunctions._functions["always_success"] = always_success
    username = "deleted_user"
    user = factories.User()
    username = user["name"]
    user = model.User.get(username)
    user.delete()
    assert not authz.is_authorized_boolean("always_success", {"user": username})
    del authz._AuthFunctions._functions["always_success"]


@pytest.mark.usefixtures("non_clean_db")
def test_only_sysadmins_can_delete_users():
    user = factories.User()
    sysadmin = factories.Sysadmin()
    context = {"model": model, "user": user["name"]}
    with pytest.raises(logic.NotAuthorized):
        assert not helpers.call_auth("user_delete", context=context, id=user["id"])

    context = {"model": model, "user": sysadmin["name"]}
    assert helpers.call_auth("user_delete", context=context, id=user["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_anon_cant_delete():
    context = {"user": None, "model": model}
    params = {}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_delete", context=context, **params)


@pytest.mark.usefixtures("non_clean_db")
def test_no_org_user_cant_delete():
    user = factories.User()
    org = factories.Organization()
    dataset = factories.Dataset(
        owner_org=org["id"], resources=[{"url": "https://example.com/data.csv"}]
    )

    response = auth_resource.resource_delete(
        {"user": user["name"], "model": model},
        {"id": dataset["resources"][0]["id"]},
    )

    assert not response["success"]


@pytest.mark.usefixtures("non_clean_db")
def test_org_user_can_delete():
    user = factories.User()
    org_users = [{"name": user["name"], "capacity": "editor"}]
    org = factories.Organization(users=org_users)
    dataset = factories.Dataset(
        owner_org=org["id"],
        resources=[{"url": "https://example.com/data.csv"}],
        user=user,
    )

    response = auth_resource.resource_delete(
        {"user": user["name"], "model": model, "auth_user_obj": user},
        {"id": dataset["resources"][0]["id"]},
    )

    assert response["success"]


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_anon_cant_delete_2():
    context = {"user": None, "model": model}
    params = {}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_view_delete", context=context, **params)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_no_org_user_cant_delete_2():
    user = factories.User()
    org = factories.Organization()
    dataset = factories.Dataset(
        owner_org=org["id"], resources=[{"url": "https://example.com/data.csv"}]
    )

    resource_view = factories.ResourceView(resource_id=dataset["resources"][0]["id"])

    context = {"user": user["name"], "model": model}

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "resource_view_delete", context=context, id=resource_view["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_org_user_can_delete_2():
    user = factories.User()
    org_users = [{"name": user["name"], "capacity": "editor"}]
    org = factories.Organization(users=org_users)
    dataset = factories.Dataset(
        owner_org=org["id"],
        resources=[{"url": "https://example.com/data.csv"}],
        user=user,
    )

    resource_view = factories.ResourceView(resource_id=dataset["resources"][0]["id"])

    context = {"user": user["name"], "model": model}

    response = helpers.call_auth(
        "resource_view_delete", context=context, id=resource_view["id"]
    )

    assert response


def test_anon_cant_clear():
    context = {"user": None, "model": model}
    params = {}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_view_clear", context=context, **params)


@pytest.mark.usefixtures("non_clean_db")
def test_normal_user_cant_clear():
    user = factories.User()

    context = {"user": user["name"], "model": model}

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("resource_view_clear", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_user_can_clear():
    user = factories.User(sysadmin=True)

    context = {"user": user["name"], "model": model}
    response = helpers.call_auth("resource_view_clear", context=context)

    assert response


def test_anon_is_not_allowed_to_revoke_tokens():
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("api_token_revoke", {"user": None, "model": model})


@pytest.mark.usefixtures("non_clean_db")
def test_auth_user_is_allowed_to_revoke_tokens():
    user = factories.User()
    token = model.ApiToken(user["id"])
    model.Session.add(token)
    model.Session.commit()

    helpers.call_auth(
        "api_token_revoke",
        {"model": model, "user": user["name"]},
        jti=token.id,
    )


@pytest.mark.usefixtures("non_clean_db")
def test_auth_user_is_allowed_to_revoke_unowned_tokens():
    owner = factories.User()
    not_owner = factories.User()
    token = model.ApiToken(owner["id"])
    model.Session.add(token)
    model.Session.commit()

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "api_token_revoke",
            {"model": model, "user": not_owner["name"]},
            jti=token.id,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_auth_user_is_allowed_to_revoke_unexisting_tokens():
    user = factories.User()

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "api_token_revoke",
            {"model": model, "user": user["name"]},
            jti="not-exists",
        )


@pytest.mark.ckan_config("ckan.auth.public_user_details", False)
@mock.patch("flask_login.utils._get_user")
def test_auth_user_list(current_user):
    current_user.return_value = mock.Mock(is_anonymous=True)
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


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.public_user_details", False)
@mock.patch("flask_login.utils._get_user")
def test_restrict_anon_auth_when_user_is_anonymouus(current_user):
    fred = factories.User()
    fred["capacity"] = "editor"
    current_user.return_value = mock.Mock(is_anonymous=True)
    context = {"user": None, "model": model}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_show", context=context, id=fred["id"])


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.public_user_details", False)
@mock.patch("flask_login.utils._get_user")
def test_restrict_anon_auth_when_user_is_in_context(current_user):
    fred = factories.User()
    fred["capacity"] = "editor"
    current_user.return_value = mock.Mock(is_anonymous=True)
    context = {"user": fred["id"], "model": model}
    assert helpers.call_auth("user_show", context=context, id=fred["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_authed_user_show():
    fred = factories.User()
    fred["capacity"] = "editor"
    context = {"user": None, "model": model}
    assert helpers.call_auth("user_show", context=context, id=fred["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_anon_is_not_allowed_to_get_tokens():
    user = factories.User()
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "api_token_list", {"user": None, "model": model}, user_id=user["name"]
        )


@pytest.mark.usefixtures("non_clean_db")
def test_auth_user_is_allowed_to_list_tokens():
    user = factories.User()
    helpers.call_auth(
        "api_token_list", {"model": model, "user": user["name"]}, user_id=user["name"]
    )


class TestFollower:
    functions = [
        "user_follower_list",
        "dataset_follower_list",
        "group_follower_list",
        "organization_follower_list",
    ]

    @pytest.mark.parametrize("func", functions)
    def test_anon_cannot_list_followers(self, func):
        context = {"user": "", "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(func, context=context)

    @pytest.mark.usefixtures("non_clean_db")
    @pytest.mark.parametrize("func", functions)
    def test_user_cannot_list_followers(self, func):
        user = factories.User()
        context = {"user": user["name"], "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(func, context=context)

    @pytest.mark.usefixtures("non_clean_db")
    @pytest.mark.parametrize("func", functions)
    def test_sysadmin_can_list_followers(self, func):
        sysadmin = factories.Sysadmin()
        context = {"user": sysadmin["name"], "model": model}
        assert helpers.call_auth(func, context=context)


class TestFollowee:
    functions = [
        "user_followee_list",
        "dataset_followee_list",
        "group_followee_list",
        "organization_followee_list",
    ]

    @pytest.mark.parametrize("func", functions)
    def test_anon_cannot_list_followees(self, func):
        context = {"user": "", "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(func, context=context)

    @pytest.mark.usefixtures("non_clean_db")
    @pytest.mark.parametrize("func", functions)
    def test_user_cannot_list_followees_of_another_user(self, func):
        user = factories.User()
        context = {"user": user["name"], "model": model}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(func, context=context)

    @pytest.mark.usefixtures("non_clean_db")
    @pytest.mark.parametrize("func", functions)
    def test_user_can_list_own_followees(self, func):
        user = factories.User()
        context = {"user": user["name"], "model": model}
        assert helpers.call_auth(func, context=context, id=user["id"])

    @pytest.mark.usefixtures("non_clean_db")
    @pytest.mark.parametrize("func", functions)
    def test_sysadmin_can_list_followees(self, func):
        sysadmin = factories.Sysadmin()
        context = {"user": sysadmin["name"], "model": model}
        assert helpers.call_auth(func, context=context)


@pytest.mark.usefixtures("non_clean_db")
class TestFolloweeCount:
    functions = [
        "dataset_followee_count",
        "followee_count",
        "group_followee_count",
        "organization_followee_count",
        "user_followee_count",
    ]

    @pytest.mark.parametrize("func", functions)
    def test_anonymous_can_see_followee_count(self, func):
        user = factories.User()
        context = {"user": "", "model": model}
        assert helpers.call_auth(func, context, id=user["id"])


@pytest.mark.usefixtures("non_clean_db")
class TestFollowerCount:
    functions = [
        "dataset_follower_count",
        "group_follower_count",
        "organization_follower_count",
        "user_follower_count",
    ]

    @pytest.mark.parametrize("func", functions)
    def test_anonymous_can_see_follower_count(self, func):
        user = factories.User()
        context = {"user": "", "model": model}
        assert helpers.call_auth(func, context, id=user["id"])


@pytest.mark.usefixtures("non_clean_db")
class TestAmFollowing:
    functions = [
        "am_following_dataset",
        "am_following_group",
        "am_following_user",
    ]

    @pytest.mark.parametrize("func", functions)
    def test_anonymous_can_see_am_following(self, func):
        user = factories.User()
        context = {"user": "", "model": model}
        assert helpers.call_auth(func, context, id=user["id"])


def test_user_update_visitor_cannot_update_user():
    """Visitors should not be able to update users' accounts."""

    # Make a mock ckan.model.User object, Fred.
    fred = factories.MockUser()

    # Make a mock ckan.model object.
    mock_model = mock.MagicMock()
    # model.User.get(user_id) should return Fred.
    mock_model.User.get.return_value = fred

    # Put the mock model in the context.
    # This is easier than patching import ckan.model.
    context = {"model": mock_model}

    # No user is going to be logged-in.
    context["user"] = "127.0.0.1"

    # Make the visitor try to update Fred's user account.
    params = {"id": fred.id, "name": "updated_user_name"}

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_update", context=context, **params)


def test_user_update_user_cannot_update_another_user():
    """Users should not be able to update other users' accounts."""

    # 1. Setup.

    # Make a mock ckan.model.User object, Fred.
    fred = factories.MockUser()

    # Make a mock ckan.model object.
    mock_model = mock.MagicMock()
    # model.User.get(user_id) should return Fred.
    mock_model.User.get.return_value = fred

    # Put the mock model in the context.
    # This is easier than patching import ckan.model.
    context = {"model": mock_model}

    # The logged-in user is going to be Bob, not Fred.
    context["user"] = "bob"

    # 2. Call the function that's being tested, once only.

    # Make Bob try to update Fred's user account.
    params = {"id": fred.id, "name": "updated_user_name"}

    # 3. Make assertions about the return value and/or side-effects.

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_update", context=context, **params)


@pytest.mark.usefixtures("non_clean_db")
def test_user_update_user_can_update_her():
    """Users should be authorized to update their own accounts."""
    fred = factories.User()

    # The 'user' in the context has to match fred.name, so that the
    # auth function thinks that the user being updated is the same user as
    # the user who is logged-in.
    context = {"user": fred["name"]}

    # Make Fred try to update his own user name.
    params = {"id": fred["id"], "name": "updated_user_name"}

    result = helpers.call_auth("user_update", context=context, **params)
    assert result is True


def test_user_update_with_no_user_in_context():

    # Make a mock ckan.model.User object.
    mock_user = factories.MockUser()

    # Make a mock ckan.model object.
    mock_model = mock.MagicMock()
    # model.User.get(user_id) should return our mock user.
    mock_model.User.get.return_value = mock_user

    # Put the mock model in the context.
    # This is easier than patching import ckan.model.
    context = {"model": mock_model}

    # For this test we're going to have no 'user' in the context.
    context["user"] = None

    params = {"id": mock_user.id, "name": "updated_user_name"}

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("user_update", context=context, **params)
