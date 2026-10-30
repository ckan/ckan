"""Tests for actions and authorization in ckan/logic/action/user.py."""

import datetime
import uuid
from unittest import mock

import pytest
import sqlalchemy as sa

from ckan import logic, model
from ckan.lib import api_token
from ckan.logic import ValidationError
from ckan.plugins.toolkit import config
from ckan.tests import factories, helpers


@pytest.mark.usefixtures("non_clean_db")
class TestUserInvite(object):
    @mock.patch("ckan.lib.mailer.send_invite")
    def test_invited_user_is_created_as_pending(self, _):
        invited_user = self._invite_user_to_group(factories.User.stub().email)

        assert invited_user is not None
        assert invited_user.is_pending()

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_creates_user_with_valid_username(self, _):
        name = factories.User.stub().name
        email = f"user$%+abc@{name}.com"
        invited_user = self._invite_user_to_group(email)

        assert invited_user.name.startswith("user---abc"), invited_user

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_assigns_user_to_group_in_expected_role(self, _):
        role = "admin"
        invited_user = self._invite_user_to_group(
            factories.User.stub().email, role=role
        )

        group_ids = invited_user.get_group_ids(capacity=role)
        assert len(group_ids) == 1, group_ids

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_sends_invite(self, send_invite):
        invited_user = self._invite_user_to_group(factories.User.stub().email)

        assert send_invite.called
        assert send_invite.call_args[0][0].id == invited_user.id

    @mock.patch("ckan.lib.mailer.send_invite")
    @mock.patch("random.SystemRandom")
    def test_works_even_if_username_already_exists(self, rand, _):
        # usernames
        rand.return_value.random.side_effect = [1000, 1000, 2000, 3000]
        # passwords (need to set something, otherwise choice will break)
        rand.return_value.choice.side_effect = "TestPassword1" * 3
        name = factories.User.stub().name
        for _ in range(3):
            invited_user = self._invite_user_to_group(
                email="same{}@{}.com".format(_, name)
            )
            assert invited_user is not None, invited_user

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_requires_email(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(email=None)

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_existed_email(self, _):
        factories.User(email="email@example.com")
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(email="email@example.com")

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_requires_role(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(factories.User.stub().email, role=None)

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_raises_not_found(self, _):
        user = factories.User()

        context = {"user": user["name"]}
        params = {
            "email": "a@example.com",
            "group_id": "group_not_found",
            "role": "admin",
        }
        with pytest.raises(logic.NotFound):
            helpers.call_action("user_invite", context, **params)

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_requires_group_id(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(factories.User.stub().email, group={"id": None})

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_user_name_lowercase_when_email_is_uppercase(self, _):
        name = factories.User.stub().name
        invited_user = self._invite_user_to_group(email=f"Maria@{name}.com")

        assert invited_user.name.split("-")[0] == "maria"

    @pytest.mark.ckan_config("smtp.server", "email.example.com")
    @pytest.mark.usefixtures("with_request_context")
    def test_smtp_error_returns_error_message(self):

        sysadmin = factories.Sysadmin()
        group = factories.Group()

        context = {"user": sysadmin["name"]}
        params = {
            "email": "example-invited-user@example.com",
            "group_id": group["id"],
            "role": "editor",
        }

        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_invite", context, **params)

        # Check that the pending user was deleted
        user = (
            model.Session.query(model.User)
            .filter(model.User.name.like("example-invited-user%"))
            .all()
        )

        assert user[0].state == "deleted"

    def _invite_user_to_group(self, email, group=None, role="member"):
        user = factories.User()
        group = group or factories.Group(user=user)

        context = {"user": user["name"]}
        params = {"email": email, "group_id": group["id"], "role": role}

        result = helpers.call_action("user_invite", context, **params)

        return model.User.get(result["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_user_create_with_password_hash():
    sysadmin = factories.Sysadmin()
    context = {"user": sysadmin["name"]}

    user = helpers.call_action(
        "user_create",
        context=context,
        email=factories.User.stub().email,
        name=factories.User.stub().name,
        password_hash="pretend-this-is-a-valid-hash",
    )

    user_obj = model.User.get(user["id"])
    assert user_obj.password == "pretend-this-is-a-valid-hash"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_user_create_password_hash_not_for_normal_users():
    normal_user = factories.User()
    context = {"user": normal_user["name"], "ignore_auth": False}

    user = helpers.call_action(
        "user_create",
        context=context,
        email=factories.User.stub().email,
        name=factories.User.stub().name,
        password="required",
        password_hash="pretend-this-is-a-valid-hash",
    )

    user_obj = model.User.get(user["id"])
    assert user_obj.password != "pretend-this-is-a-valid-hash"


@pytest.mark.usefixtures("non_clean_db")
def test_user_create_basic_fields():
    email = factories.User.stub().email
    name = factories.User.stub().name
    user = helpers.call_action(
        "user_create",
        email=email,
        name=name,
        password="required",
    )
    assert user["email"] == email
    assert user["name"] == name
    assert "password" not in user


@pytest.mark.usefixtures("non_clean_db")
def test_user_create_parameters_missing():
    with pytest.raises(logic.ValidationError) as err:
        helpers.call_action("user_create")
    assert err.value.error_dict == {
        "email": ["Missing value"],
        "name": ["Missing value"],
        "password": ["Missing value"],
    }


@pytest.mark.usefixtures("non_clean_db")
def test_user_create_wrong_password():
    stub = factories.User.stub()
    user_dict = {
        "name": stub.name,
        "email": stub.email,
        "password": "tes",
    }  # Too short

    with pytest.raises(logic.ValidationError) as err:
        helpers.call_action("user_create", **user_dict)
    assert err.value.error_dict == {
        "password": ["Your password must be 8 characters or longer"]
    }


@pytest.mark.usefixtures("non_clean_db")
def test_user_create_defer_commit():
    stub = factories.User.stub()
    user_dict = {
        "name": stub.name,
        "email": stub.email,
        "password": "test1234",
    }
    context = {"defer_commit": True}

    helpers.call_action("user_create", context=context, **user_dict)

    model.Session.close()

    with pytest.raises(logic.NotFound):
        helpers.call_action("user_show", id=user_dict["name"])


@pytest.mark.usefixtures("non_clean_db")
def test_create_user_with_apitoken():
    stub = factories.User.stub()
    context = {"ignore_auth": True}
    user_dict = {
        "name": stub.name,
        "email": stub.email,
        "password": "test1234",
        "with_apitoken": True,
    }
    user = helpers.call_action("user_create", context={}, **user_dict)
    assert user["token"]

    user_dict = {"user_id": user["name"]}
    token = helpers.call_action("api_token_list", context=context, **user_dict)
    assert len(token) == 1


@pytest.mark.usefixtures("non_clean_db")
def test_create_user_with_apitoken_missing_flag():
    stub = factories.User.stub()
    context = {"ignore_auth": True}
    user_dict = {
        "name": stub.name,
        "email": stub.email,
        "password": "test1234",
    }
    user = helpers.call_action("user_create", context={}, **user_dict)
    assert "token" not in user

    user_dict = {"user_id": user["name"]}
    token = helpers.call_action("api_token_list", context=context, **user_dict)
    assert not token


@pytest.mark.usefixtures("non_clean_db")
def test_user_create_fails_with_duplicate_email_case_insensitive():
    factories.User(email="some_email@example.org")

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "user_create",
            context={},
            email="Some_Email@example.org",
            name="test",
            password="required",
        )


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_anon_user_create_does_not_update():
    user1 = factories.User(about="This is user 1")
    user_dict = {
        "id": user1["id"],
        "name": "some_name",
        "email": "some_email@example.com",
        "password": "test1234",
    }

    context = {
        "user": None,
        "ignore_auth": False,
    }

    user2 = helpers.call_action("user_create", context=context, **user_dict)
    assert user2["id"] != user1["id"]
    assert user2["about"] != "This is user 1"


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_normal_user_create_does_not_update():
    user1 = factories.User(about="This is user 1")
    user_dict = {
        "id": user1["id"],
        "name": "some_name",
        "email": "some_email@example.com",
        "password": "test1234",
    }

    context = {
        "user": factories.User()["name"],
        "ignore_auth": False,
    }

    user2 = helpers.call_action("user_create", context=context, **user_dict)
    assert user2["id"] != user1["id"]
    assert user2["about"] != "This is user 1"


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_sysadmin_user_create_does_not_update():
    user1 = factories.User(about="This is user 1")
    user_dict = {
        "id": user1["id"],
        "name": "some_name",
        "email": "some_email@example.com",
        "password": "test1234",
    }

    context = {
        "user": factories.Sysadmin()["name"],
        "ignore_auth": False,
    }

    user2 = helpers.call_action("user_create", context=context, **user_dict)
    assert user2["id"] != user1["id"]
    assert user2["about"] != "This is user 1"


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_anon_users_can_not_provide_custom_id():

    user_dict = {
        "id": "custom_id",
        "name": "some_name",
        "email": "some_email@example.com",
        "password": "test1234",
    }

    context = {
        "user": None,
        "ignore_auth": False,
    }

    user = helpers.call_action("user_create", context=context, **user_dict)
    assert user["id"] != "custom_id"


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_normal_users_can_not_provide_custom_id():

    user_dict = {
        "id": "custom_id",
        "name": "some_name",
        "email": "some_email@example.com",
        "password": "test1234",
    }

    context = {
        "user": factories.User()["name"],
        "ignore_auth": False,
    }

    user = helpers.call_action("user_create", context=context, **user_dict)
    assert user["id"] != "custom_id"


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_sysadmin_can_provide_custom_id():
    _id = str(uuid.uuid4())
    user_dict = {
        "id": _id,
        "name": "some_name",
        "email": "some_email@example.com",
        "password": "test1234",
    }
    context = {
        "user": factories.Sysadmin()["name"],
        "ignore_auth": False,
    }

    user = helpers.call_action("user_create", context=context, **user_dict)
    assert user["id"] == _id


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_unique_emails():
    """
    Active users can only have one unique associated email address.
    This should be case insensitive.
    """
    factories.User(email="example_email@example.com")

    bad_emails = [
        "example_email@example.com",
        "ExAmPlE_eMaIl@example.com",
        "EXAMPLE_EMAIL@EXAMPLE.COM",
    ]

    for bad_email in bad_emails:
        with pytest.raises(logic.ValidationError) as err:
            factories.User(email=bad_email)
        assert err.value.error_dict == {
            "email": [
                "The email address 'example_email@example.com' belongs to a registered user."
            ]
        }


@pytest.mark.usefixtures("non_clean_db")
def test_validation():
    user = factories.User()
    unfollow_actions = (
        "unfollow_user",
        "unfollow_dataset",
        "unfollow_group",
    )
    follow_actions = ("follow_user", "follow_dataset", "follow_group")
    count_actions = (
        "user_follower_count",
        "dataset_follower_count",
        "group_follower_count",
    )
    list_actions = (
        "user_follower_list",
        "dataset_follower_list",
        "group_follower_list",
    )
    my_actions = (
        "am_following_dataset",
        "am_following_user",
        "am_following_group",
    )
    for action in (
        follow_actions + unfollow_actions + count_actions + list_actions + my_actions
    ):
        for object_id in ("bad id", "     ", 3, 35.7, "xxx", None, ""):
            with pytest.raises(logic.ValidationError):
                context = {"user": user["name"]}
                helpers.call_action(action, context, id=object_id)


@pytest.mark.usefixtures("non_clean_db")
def test_auth():
    user = factories.User()
    dataset = factories.Dataset()
    context = {"user": "", "ignore_auth": False}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_action("follow_dataset", context, id=dataset["id"])
    context = {"user": user["name"], "ignore_auth": False}
    helpers.call_action("follow_dataset", context, id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_cannot_follow_private_dataset_without_read_access():
    owner = factories.User()
    org = factories.Organization(user=owner)
    dataset = factories.Dataset(user=owner, owner_org=org["id"], private=True)
    user = factories.User()

    context = {"user": user["name"], "ignore_auth": False}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_action("follow_dataset", context, id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_can_follow_private_dataset_with_read_access():
    owner = factories.User()
    org = factories.Organization(user=owner)
    dataset = factories.Dataset(user=owner, owner_org=org["id"], private=True)

    context = {"user": owner["name"], "ignore_auth": False}
    helpers.call_action("follow_dataset", context, id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_follow_dataset():
    user = factories.User()
    dataset = factories.Dataset()
    context = {"user": user["name"]}
    assert helpers.call_action("dataset_follower_count", id=dataset["id"]) == 0
    assert helpers.call_action("dataset_follower_list", id=dataset["id"]) == []
    assert not helpers.call_action("am_following_dataset", context, id=dataset["id"])

    helpers.call_action("follow_dataset", context, id=dataset["id"])
    assert helpers.call_action("dataset_follower_count", id=dataset["id"]) == 1
    assert [
        u["name"]
        for u in helpers.call_action("dataset_follower_list", id=dataset["id"])
    ] == [user["name"]]
    assert helpers.call_action("am_following_dataset", context, id=dataset["id"])

    helpers.call_action("unfollow_dataset", context, id=dataset["id"])
    assert helpers.call_action("dataset_follower_count", id=dataset["id"]) == 0
    assert helpers.call_action("dataset_follower_list", id=dataset["id"]) == []
    assert not helpers.call_action("am_following_dataset", context, id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_followgroup_auth():
    user = factories.User()
    group = factories.Group()
    context = {"user": "", "ignore_auth": False}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_action("follow_group", context, id=group["id"])
    context = {"user": user["name"], "ignore_auth": False}
    helpers.call_action("follow_group", context, id=group["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_follow_group():
    user = factories.User()
    group = factories.Group()
    context = {"user": user["name"]}
    assert helpers.call_action("group_follower_count", id=group["id"]) == 0
    assert helpers.call_action("group_follower_list", id=group["id"]) == []
    assert not helpers.call_action("am_following_group", context, id=group["id"])

    helpers.call_action("follow_group", context, id=group["id"])
    assert helpers.call_action("group_follower_count", id=group["id"]) == 1
    assert [
        u["name"] for u in helpers.call_action("group_follower_list", id=group["id"])
    ] == [user["name"]]
    assert helpers.call_action("am_following_group", context, id=group["id"])

    helpers.call_action("unfollow_group", context, id=group["id"])
    assert helpers.call_action("group_follower_count", id=group["id"]) == 0
    assert helpers.call_action("group_follower_list", id=group["id"]) == []
    assert not helpers.call_action("am_following_group", context, id=group["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_followorganization_auth_create():
    user = factories.User()
    organization = factories.Organization()
    context = {"user": "", "ignore_auth": False}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_action("follow_group", context, id=organization["id"])
    context = {"user": user["name"], "ignore_auth": False}
    helpers.call_action("follow_group", context, id=organization["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_follow_organization():
    user = factories.User()
    group = factories.Organization()
    context = {"user": user["name"]}
    assert helpers.call_action("group_follower_count", id=group["id"]) == 0
    assert helpers.call_action("group_follower_list", id=group["id"]) == []
    assert not helpers.call_action("am_following_group", context, id=group["id"])

    helpers.call_action("follow_group", context, id=group["id"])
    assert helpers.call_action("group_follower_count", id=group["id"]) == 1
    assert [
        u["name"] for u in helpers.call_action("group_follower_list", id=group["id"])
    ] == [user["name"]]
    assert helpers.call_action("am_following_group", context, id=group["id"])

    helpers.call_action("unfollow_group", context, id=group["id"])
    assert helpers.call_action("group_follower_count", id=group["id"]) == 0
    assert helpers.call_action("group_follower_list", id=group["id"]) == []
    assert not helpers.call_action("am_following_group", context, id=group["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_followuser_auth_create():
    user = factories.User()
    second_user = factories.User()

    context = {"user": "", "ignore_auth": False}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_action("follow_user", context, id=second_user["id"])
    context = {"user": user["name"], "ignore_auth": False}
    helpers.call_action("follow_user", context, id=second_user["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_cannot_follow_myself():
    user = factories.User()
    context = {"user": user["name"]}
    with pytest.raises(logic.ValidationError):
        helpers.call_action("follow_user", context, id=user["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_follow_user():
    user = factories.User()
    another_user = factories.User()
    context = {"user": user["name"]}
    assert helpers.call_action("user_follower_count", id=another_user["id"]) == 0
    assert helpers.call_action("user_follower_list", id=another_user["id"]) == []
    assert not helpers.call_action("am_following_user", context, id=another_user["id"])

    helpers.call_action("follow_user", context, id=another_user["id"])
    assert helpers.call_action("user_follower_count", id=another_user["id"]) == 1
    assert [
        u["name"]
        for u in helpers.call_action("user_follower_list", id=another_user["id"])
    ] == [user["name"]]
    assert helpers.call_action("am_following_user", context, id=another_user["id"])

    helpers.call_action("unfollow_user", context, id=another_user["id"])
    assert helpers.call_action("user_follower_count", id=another_user["id"]) == 0
    assert helpers.call_action("user_follower_list", id=another_user["id"]) == []
    assert not helpers.call_action("am_following_user", context, id=another_user["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_token_created():
    from ckan.lib.api_token import decode

    user = factories.User()
    data = helpers.call_action(
        "api_token_create",
        context={"model": model, "user": user["name"]},
        user=user["name"],
        name="token-name",
    )
    token = data["token"]
    jti = decode(token)["jti"]
    res = model.ApiToken.get(jti)
    assert res.user_id == user["id"]
    assert res.last_access is None
    assert res.id == jti


@pytest.mark.usefixtures("non_clean_db")
def test_token_created_insert():
    """
    Sysadmins should be able to insert id, created_at, last_access
    """
    from ckan.lib.api_token import decode

    # normal users cannot insert API Tokens
    user = factories.User()
    data = helpers.call_action(
        "api_token_create",
        context={"model": model, "user": user["name"], "ignore_auth": False},
        user=user["name"],
        name="token-name-create",
        id="thisisthetoken",
        created_at="2025-09-12T19:06:35.989399",
        last_access="2025-09-12T19:06:35.989399",
    )
    token = data["token"]
    jti = decode(token)["jti"]
    res = model.ApiToken.get(jti)
    assert res.user_id == user["id"]
    assert res.last_access != datetime.datetime.fromisoformat(
        "2025-09-12T19:06:35.989399"
    )
    assert res.created_at != datetime.datetime.fromisoformat(
        "2025-09-12T19:06:35.989399"
    )
    assert res.id == jti
    assert res.id != "thisisthetoken"

    # sysadmin users can insert API Tokens
    user = factories.Sysadmin()
    data = helpers.call_action(
        "api_token_create",
        context={"model": model, "user": user["name"], "ignore_auth": False},
        user=user["name"],
        name="token-name-create",
        id="thisisthetoken",
        created_at="2025-09-12T19:06:35.989399",
        last_access="2025-09-12T19:06:35.989399",
    )
    token = data["token"]
    jti = decode(token)["jti"]
    res = model.ApiToken.get(jti)
    assert res.user_id == user["id"]
    assert res.last_access == datetime.datetime.fromisoformat(
        "2025-09-12T19:06:35.989399"
    )
    assert res.created_at == datetime.datetime.fromisoformat(
        "2025-09-12T19:06:35.989399"
    )
    assert res.id == jti
    assert res.id == "thisisthetoken"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_stored_on_create_if_sysadmin():

    sysadmin = factories.Sysadmin()
    stub = factories.User.stub()
    user_dict = {
        "name": stub.name,
        "email": stub.email,
        "password": "12345678",
        "plugin_extras": {"plugin1": {"key1": "value1"}},
    }

    # helpers.call_action sets 'ignore_auth' to True by default
    context = {"user": sysadmin["name"], "ignore_auth": False}

    created_user = helpers.call_action("user_create", context=context, **user_dict)

    assert created_user["plugin_extras"] == {
        "plugin1": {
            "key1": "value1",
        }
    }

    user_dict = helpers.call_action(
        "user_show",
        context=context,
        id=created_user["id"],
        include_plugin_extras=True,
    )

    assert user_dict["plugin_extras"] == {
        "plugin1": {
            "key1": "value1",
        }
    }

    plugin_extras_from_db = model.Session.execute(
        sa.text('SELECT plugin_extras FROM "user" WHERE id=:id'),
        {"id": created_user["id"]},
    ).first()[0]

    assert plugin_extras_from_db == {
        "plugin1": {
            "key1": "value1",
        }
    }


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_ignored_on_create_if_non_sysadmin():

    author = factories.User()
    sysadmin = factories.Sysadmin()
    stub = factories.User.stub()
    user_dict = {
        "name": stub.name,
        "email": stub.email,
        "password": "12345678",
        "plugin_extras": {"plugin1": {"key1": "value1"}},
    }

    # helpers.call_action sets 'ignore_auth' to True by default
    context = {"user": author["name"], "ignore_auth": False}

    created_user = helpers.call_action("user_create", context=context, **user_dict)

    assert "plugin_extras" not in created_user

    context = {"user": sysadmin["name"], "ignore_auth": False}
    user = helpers.call_action(
        "user_show",
        context=context,
        id=created_user["id"],
        include_plugin_extras=True,
    )

    assert user["plugin_extras"] is None


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
def test_extensions_can_provide_custom_id():

    stub = factories.User.stub()
    context = {"user": None, "ignore_auth": True}
    _id = str(uuid.uuid4())
    user_dict = {
        "id": _id,
        "name": stub.name,
        "email": stub.email,
        "password": "12345678",
    }
    created_user = helpers.call_action("user_create", context=context, **user_dict)

    assert created_user["id"] == _id


@pytest.mark.usefixtures("clean_db")
def test_external_picture():
    stub = factories.User.stub()
    params = {
        "name": stub.name,
        "email": stub.email,
        "password": "12345678",
        "image_url": "https://example.com/mypic.png",
    }

    user_dict = helpers.call_action("user_create", {}, **params)

    assert user_dict["image_url"] == "https://example.com/mypic.png"
    assert user_dict["image_display_url"] == "https://example.com/mypic.png"


@pytest.mark.usefixtures("clean_db")
def test_upload_picture_works_without_extra_config(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    assert create_with_upload(faker.image(), "image.png", **params)


@pytest.mark.usefixtures("clean_db")
def test_upload_non_picture_fails_without_extra_config(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    with pytest.raises(logic.ValidationError, match="Type .+ is not supported"):
        create_with_upload("hello world", "file.txt", **params)


@pytest.mark.usefixtures("clean_db")
def test_upload_non_picture_html_fails_without_extra_config(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    with pytest.raises(logic.ValidationError, match="Type .+ is not supported"):
        create_with_upload(
            "<html><body>hello world</body></html>", "file.html", **params
        )


@pytest.mark.usefixtures("clean_db")
def test_upload_svg_fails_without_extra_config(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    with pytest.raises(logic.ValidationError, match="Type .+ is not supported"):
        create_with_upload(
            '<svg xmlns="http://www.w3.org/2000/svg"></svg>', "file.svg", **params
        )


@pytest.mark.usefixtures("clean_db")
def test_upload_svg_wrong_extension_fails_without_extra_config(
    create_with_upload, faker
):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    with pytest.raises(logic.ValidationError, match="Type .+ is not supported"):
        create_with_upload(
            '<svg xmlns="http://www.w3.org/2000/svg"></svg>', "file.png", **params
        )


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.upload.user.types", ["image"])
def test_upload_non_picture_with_png_extension(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    with pytest.raises(logic.ValidationError, match="Type .+ is not supported"):
        create_with_upload("hello world", "file.png", **params)


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.upload.user.mimetypes", ["image/png"])
@pytest.mark.ckan_config("ckan.upload.user.types", ["*"])
def test_upload_mimetype_has_higher_priority(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    with pytest.raises(logic.ValidationError, match="Type .+ is not supported"):
        assert create_with_upload(faker.json(), "file.json", **params)


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.upload.user.mimetypes", ["*"])
@pytest.mark.ckan_config("ckan.upload.user.types", ["*"])
def test_upload_all_types_allowed(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    assert create_with_upload(faker.json(), "file.json", **params)


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.upload.user.types", ["image"])
def test_upload_picture(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    assert create_with_upload(faker.image(), "file.png", **params)


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.upload.user.types", ["image"])
def test_upload_picture_extension_enforced(create_with_upload, faker):
    params = {
        "name": faker.user_name(),
        "email": faker.email(),
        "password": "12345678",
        "action": "user_create",
        "upload_field_name": "image_upload",
    }
    user = create_with_upload(faker.image(image_format="jpeg"), "file.png", **params)

    assert user["image_url"].endswith(".jpg")
    assert user["image_display_url"].endswith(".jpg")


@pytest.mark.usefixtures("non_clean_db")
def test_user_delete():
    user = factories.User()
    context = {}
    params = {"id": user["id"]}

    helpers.call_action("user_delete", context, **params)

    # It is still there but with state=deleted
    user_obj = model.User.get(user["id"])
    assert user_obj.state == "deleted"


@pytest.mark.usefixtures("non_clean_db")
def test_user_delete_but_user_doesnt_exist():
    context = {}
    params = {"id": "unknown"}

    with pytest.raises(logic.NotFound):
        helpers.call_action("user_delete", context, **params)


@pytest.mark.usefixtures("non_clean_db")
def test_user_delete_removes_memberships():
    user = factories.User()
    factories.Organization(users=[{"name": user["id"], "capacity": "admin"}])

    factories.Group(users=[{"name": user["id"], "capacity": "admin"}])

    user_memberships = (
        model.Session.query(model.Member)
        .filter(model.Member.table_id == user["id"])
        .all()
    )

    assert len(user_memberships) == 2

    assert [m.state for m in user_memberships] == ["active", "active"]

    context = {}
    params = {"id": user["id"]}

    helpers.call_action("user_delete", context, **params)

    user_memberships = (
        model.Session.query(model.Member)
        .filter(model.Member.table_id == user["id"])
        .all()
    )

    # Member objects are still there, but flagged as deleted
    assert len(user_memberships) == 2

    assert [m.state for m in user_memberships] == ["deleted", "deleted"]


@pytest.mark.usefixtures("non_clean_db")
def test_user_delete_removes_memberships_when_using_name():
    user = factories.User()
    factories.Organization(users=[{"name": user["id"], "capacity": "admin"}])

    factories.Group(users=[{"name": user["id"], "capacity": "admin"}])

    context = {}
    params = {"id": user["name"]}

    helpers.call_action("user_delete", context, **params)

    user_memberships = (
        model.Session.query(model.Member)
        .filter(model.Member.table_id == user["id"])
        .all()
    )

    # Member objects are still there, but flagged as deleted
    assert len(user_memberships) == 2

    assert [m.state for m in user_memberships] == ["deleted", "deleted"]


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_user_delete_removes_collaborations():
    user = factories.User()
    dataset = factories.Dataset()
    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity="editor",
    )

    assert len(helpers.call_action("package_collaborator_list", id=dataset["id"])) == 1

    context = {}
    params = {"id": user["id"]}

    helpers.call_action("user_delete", context, **params)

    assert len(helpers.call_action("package_collaborator_list", id=dataset["id"])) == 0


@pytest.mark.usefixtures("non_clean_db")
def test_token_revoke():
    user = factories.User()
    token = helpers.call_action(
        "api_token_create",
        context={"model": model, "user": user["name"]},
        user=user["name"],
        name="token-name",
    )["token"]
    token2 = helpers.call_action(
        "api_token_create",
        context={"model": model, "user": user["name"]},
        user=user["name"],
        name="token-name-2",
    )["token"]

    tokens = helpers.call_action(
        "api_token_list",
        context={"model": model, "user": user["name"]},
        user_id=user["name"],
    )
    assert len(tokens) == 2

    helpers.call_action(
        "api_token_revoke",
        context={"model": model, "user": user["name"]},
        token=token,
    )

    tokens = helpers.call_action(
        "api_token_list",
        context={"model": model, "user": user["name"]},
        user_id=user["name"],
    )
    assert len(tokens) == 1

    helpers.call_action(
        "api_token_revoke",
        context={"model": model, "user": user["name"]},
        jti=api_token.decode(token2)["jti"],
    )

    tokens = helpers.call_action(
        "api_token_list",
        context={"model": model, "user": user["name"]},
        user_id=user["name"],
    )
    assert len(tokens) == 0


@pytest.mark.usefixtures("clean_db")
def test_user_list_default_values():
    user = factories.User()

    got_users = helpers.call_action(
        "user_list",
        # call_action will set ignore_auth: True by default, which will
        # include restricted fields like apikey
        context={"ignore_auth": False},
    )

    assert len(got_users) == 1
    got_user = got_users[0]
    assert got_user["id"] == user["id"]
    assert got_user["name"] == user["name"]
    assert got_user["fullname"] == user["fullname"]
    assert got_user["display_name"] == user["display_name"]
    assert got_user["created"] == user["created"]
    assert got_user["about"] == user["about"]
    assert got_user["sysadmin"] == user["sysadmin"]
    assert got_user["number_created_packages"] == 0
    assert "password" not in got_user
    assert "reset_key" not in got_user
    assert "apikey" not in got_user
    assert "email" not in got_user
    assert "datasets" not in got_user


@pytest.mark.usefixtures("clean_db")
def test_user_list_edits():
    user = factories.User()
    dataset = factories.Dataset(user=user)
    dataset["title"] = "Edited title"
    helpers.call_action("package_update", context={"user": user["name"]}, **dataset)
    got_users = helpers.call_action("user_list")

    assert len(got_users) == 1
    got_user = got_users[0]
    assert got_user["number_created_packages"] == 1


@pytest.mark.usefixtures("clean_db")
def test_include_site_user(ckan_config):
    factories.User()

    users = helpers.call_action("user_list")
    assert len(users) == 1

    users = helpers.call_action("user_list", include_site_user=True)
    assert len(users) == 2


@pytest.mark.usefixtures("clean_db")
def test_user_list_excludes_deleted_users():
    user = factories.User()
    factories.User(state="deleted")

    got_users = helpers.call_action("user_list")

    assert len(got_users) == 1
    assert got_users[0]["name"] == user["name"]


@pytest.mark.usefixtures("clean_db")
def test_user_list_not_all_fields():
    user = factories.User()

    got_users = helpers.call_action("user_list", all_fields=False)

    assert len(got_users) == 1
    got_user = got_users[0]
    assert got_user == user["name"]


@pytest.mark.usefixtures("clean_db")
def test_user_list_return_query():
    user_a = factories.User(email="a@example.com")
    query = helpers.call_action(
        "user_list", {"return_query": True}, email="a@example.com"
    )
    user = query.one()

    expected = ["name", "fullname", "about", "email"]
    for prop in expected:
        assert user_a[prop] == getattr(user, prop), prop


@pytest.mark.usefixtures("clean_db")
def test_user_list_filtered_by_email():

    user_a = factories.User(email="a@example.com")
    factories.User(email="b@example.com")

    got_users = helpers.call_action(
        "user_list", email="a@example.com", all_fields=False
    )

    assert len(got_users) == 1
    got_user = got_users[0]
    assert got_user == user_a["name"]


@pytest.mark.usefixtures("clean_db")
def test_user_list_filtered_by_email_with_random_case():
    user_a = factories.User(email="a@example.com")
    factories.User(email="b@example.com")

    got_users = helpers.call_action(
        "user_list", email="A@example.COM", all_fields=False
    )

    assert len(got_users) == 1
    got_user = got_users[0]
    assert got_user == user_a["name"]


@pytest.mark.usefixtures("clean_db")
def test_user_list_order_by_default():
    default_user = model.User.get_site_user()

    users = [
        factories.User(fullname="Xander Bird", name="bird_x"),
        factories.User(fullname="Max Hankins", name="hankins_m"),
        factories.User(fullname="", name="zoe_w"),
        factories.User(fullname="Kathy Tillman", name="tillman_k"),
    ]
    expected_names = [
        u["name"]
        for u in [
            users[3],  # Kathy Tillman
            users[1],  # Max Hankins
            users[0],  # Xander Bird
            users[2],  # zoe_w
        ]
    ]

    got_users = helpers.call_action("user_list")
    got_names = [u["name"] for u in got_users if u["name"] != default_user.name]

    assert got_names == expected_names


@pytest.mark.usefixtures("clean_db")
def test_user_list_order_by_fullname_only():
    default_user = model.User.get_site_user()

    users = [
        factories.User(fullname="Xander Bird", name="bird_x"),
        factories.User(fullname="Max Hankins", name="hankins_m"),
        factories.User(fullname="", name="morgan_w"),
        factories.User(fullname="Kathy Tillman", name="tillman_k"),
    ]
    expected_fullnames = sorted([u["fullname"] for u in users])

    got_users = helpers.call_action("user_list", order_by="fullname")
    got_fullnames = [
        u["fullname"] for u in got_users if u["name"] != default_user.name
    ]

    assert got_fullnames == expected_fullnames


@pytest.mark.usefixtures("clean_db")
def test_user_list_order_by_created_datasets():
    default_user = model.User.get_site_user()

    users = [
        factories.User(fullname="Xander Bird", name="bird_x"),
        factories.User(fullname="Max Hankins", name="hankins_m"),
        factories.User(fullname="Kathy Tillman", name="tillman_k"),
    ]
    datasets = [
        factories.Dataset(user=users[1]),
        factories.Dataset(user=users[1]),
    ]
    factories.Dataset(user=users[2])
    for dataset in datasets:
        dataset["title"] = "Edited title"
        helpers.call_action(
            "package_update", context={"user": users[1]["name"]}, **dataset
        )
    expected_names = [
        u["name"]
        for u in [
            users[0],  # 0 packages created
            users[2],  # 1 packages created
            users[1],  # 2 packages created
        ]
    ]

    got_users = helpers.call_action("user_list", order_by="number_created_packages")
    got_names = [u["name"] for u in got_users if u["name"] != default_user.name]

    assert got_names == expected_names


@pytest.mark.usefixtures("clean_db")
def test_user_list_order_by_edits():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("user_list", order_by="edits")


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_default_values():

    user = factories.User()

    got_user = helpers.call_action(
        "user_show",
        id=user["id"],
        # call_action will set ignore_auth: True by default, which will
        # include restricted fields like apikey
        context={"ignore_auth": False},
    )

    assert got_user["id"] == user["id"]
    assert got_user["name"] == user["name"]
    assert got_user["fullname"] == user["fullname"]
    assert got_user["display_name"] == user["display_name"]
    assert got_user["created"] == user["created"]
    assert got_user["about"] == user["about"]
    assert got_user["sysadmin"] == user["sysadmin"]
    assert got_user["number_created_packages"] == 0
    assert "password" not in got_user
    assert "reset_key" not in got_user
    assert "apikey" not in got_user
    assert "email" not in got_user
    assert "datasets" not in got_user
    assert "password_hash" not in got_user


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_keep_email():

    user = factories.User()

    got_user = helpers.call_action(
        "user_show",
        id=user["id"],
        # call_action will set ignore_auth: True by default, which will
        # include restricted fields like apikey
        context={"keep_email": True, "ignore_auth": False},
    )

    assert got_user["email"] == user["email"]
    assert "apikey" not in got_user
    assert "password" not in got_user
    assert "reset_key" not in got_user


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_keep_apikey():

    user = factories.User()

    got_user = helpers.call_action(
        "user_show",
        id=user["id"],
        # call_action will set ignore_auth: True by default, which will
        # include restricted fields like apikey
        context={"keep_apikey": True, "ignore_auth": False},
    )

    assert "email" not in got_user
    assert got_user["apikey"] == user["apikey"]
    assert "password" not in got_user
    assert "reset_key" not in got_user


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_normal_user_no_password_hash():

    user = factories.User()

    got_user = helpers.call_action(
        "user_show", id=user["id"], include_password_hash=True
    )

    assert "password_hash" not in got_user


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_for_myself():

    user = factories.User()

    got_user = helpers.call_action(
        "user_show", context={"user": user["name"]}, id=user["id"]
    )

    assert got_user["email"] == user["email"]
    assert got_user["apikey"] == user["apikey"]
    assert "password" not in got_user
    assert "reset_key" not in got_user


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_sysadmin_values():

    user = factories.User()

    sysadmin = factories.User(sysadmin=True)

    got_user = helpers.call_action(
        "user_show", context={"user": sysadmin["name"]}, id=user["id"]
    )

    assert got_user["email"] == user["email"]
    assert got_user["apikey"] == user["apikey"]
    assert "password" not in got_user
    assert "reset_key" not in got_user


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_sysadmin_password_hash():

    user = factories.User(password="TestPassword1")

    sysadmin = factories.User(sysadmin=True)

    got_user = helpers.call_action(
        "user_show",
        context={"user": sysadmin["name"]},
        id=user["id"],
        include_password_hash=True,
    )

    assert got_user["email"] == user["email"]
    assert got_user["apikey"] == user["apikey"]
    assert "password_hash" in got_user
    assert "password" not in got_user
    assert "reset_key" not in got_user


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_include_datasets():

    user = factories.User()
    dataset = factories.Dataset(user=user)

    got_user = helpers.call_action("user_show", include_datasets=True, id=user["id"])

    assert len(got_user["datasets"]) == 1
    assert got_user["datasets"][0]["name"] == dataset["name"]


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_include_datasets_excludes_draft_and_private():

    user = factories.User()
    org = factories.Organization(user=user)
    dataset = factories.Dataset(user=user)
    factories.Dataset(user=user, state="deleted")
    factories.Dataset(user=user, state="draft")
    factories.Dataset(user=user, private=True, owner_org=org["name"])

    got_user = helpers.call_action("user_show", include_datasets=True, id=user["id"])

    assert len(got_user["datasets"]) == 1
    assert got_user["datasets"][0]["name"] == dataset["name"]
    assert got_user["number_created_packages"] == 1


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_include_datasets_includes_draft_myself():
    # a user viewing his own user should see the draft and private datasets

    user = factories.User()
    org = factories.Organization(user=user)
    factories.Dataset(user=user)
    dataset_deleted = factories.Dataset(user=user, state="deleted")
    factories.Dataset(user=user, state="draft")
    factories.Dataset(user=user, private=True, owner_org=org["name"])

    got_user = helpers.call_action(
        "user_show",
        context={"user": user["name"]},
        include_datasets=True,
        id=user["id"],
    )

    assert len(got_user["datasets"]) == 3
    datasets_got = set([user_["name"] for user_ in got_user["datasets"]])
    assert dataset_deleted["name"] not in datasets_got
    assert got_user["number_created_packages"] == 3


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_include_datasets_includes_draft_sysadmin():
    # sysadmin should see the draft and private datasets

    user = factories.User()
    sysadmin = factories.Sysadmin()
    org = factories.Organization(user=user)
    factories.Dataset(user=user)
    dataset_deleted = factories.Dataset(user=user, state="deleted")
    factories.Dataset(user=user, state="draft")
    factories.Dataset(user=user, private=True, owner_org=org["name"])

    got_user = helpers.call_action(
        "user_show",
        context={"user": sysadmin["name"]},
        include_datasets=True,
        id=user["id"],
    )

    assert len(got_user["datasets"]) == 3
    datasets_got = set([user_["name"] for user_ in got_user["datasets"]])
    assert dataset_deleted["name"] not in datasets_got
    assert got_user["number_created_packages"] == 3


@pytest.mark.usefixtures("non_clean_db")
def test_user_show_for_myself_without_passing_id():

    user = factories.User()

    got_user = helpers.call_action("user_show", context={"user": user["name"]})

    assert got_user["name"] == user["name"]
    assert got_user["email"] == user["email"]
    assert got_user["apikey"] == user["apikey"]
    assert "password" not in got_user
    assert "reset_key" not in got_user


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_autocomplete():
    factories.Sysadmin(name="autocompletesysadmin")
    factories.User(name="autocompleteuser")
    result = helpers.call_action("user_autocomplete", q="sysadmin")
    assert len(result) == 1
    user = result.pop()
    assert set(user.keys()) == set(["id", "name", "fullname"])
    assert user["name"] == "autocompletesysadmin"


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_autocomplete_multiple():
    factories.Sysadmin(name="autocompletesysadmin")
    factories.User(name="autocompleteuser")
    result = helpers.call_action("user_autocomplete", q="compl")
    assert len(result) == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_autocomplete_limit():
    factories.Sysadmin(name="autocompletesysadmin")
    factories.User(name="autocompleteuser")
    result = helpers.call_action("user_autocomplete", q="compl", limit=1)
    assert len(result) == 1


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_autocomplete_email():
    user = factories.Sysadmin()
    context = {"user": user["name"]}
    factories.User(name="user1234", email="joe@doe.com")
    result = helpers.call_action("user_autocomplete", context=context, q="joe@doe.com")
    assert len(result) == 1
    assert result[0]["name"] == "user1234"

    # test when user is not sysadmin
    result = helpers.call_action("user_autocomplete", q="joe@doe.com")
    assert len(result) == 0


def remove_pseudo_users(user_list):
    pseudo_users = set(("logged_in", "visitor"))
    user_list[:] = [user for user in user_list if user["name"] not in pseudo_users]


@pytest.mark.usefixtures("non_clean_db")
def test_followee_list():

    group1 = factories.Group(title="Finance")
    group2 = factories.Group(title="Environment")
    factories.Group(title="Education")

    user = factories.User()

    context = {"user": user["name"]}

    helpers.call_action("follow_group", context, id=group1["id"])
    helpers.call_action("follow_group", context, id=group2["id"])

    followee_list = helpers.call_action("followee_list", context, id=user["name"])

    assert len(followee_list) == 2
    assert sorted([f["display_name"] for f in followee_list]) == [
        "Environment",
        "Finance",
    ]


@pytest.mark.usefixtures("non_clean_db")
def test_followee_list_with_q():

    group1 = factories.Group(title="Finance")
    group2 = factories.Group(title="Environment")
    factories.Group(title="Education")

    user = factories.User()

    context = {"user": user["name"]}

    helpers.call_action("follow_group", context, id=group1["id"])
    helpers.call_action("follow_group", context, id=group2["id"])

    followee_list = helpers.call_action(
        "followee_list", context, id=user["name"], q="E"
    )

    assert len(followee_list) == 1
    assert followee_list[0]["display_name"] == "Environment"


@pytest.mark.usefixtures("non_clean_db")
def test_followee_list_excludes_datasets_user_cannot_read():
    owner = factories.User()
    org = factories.Organization(user=owner)
    dataset = factories.Dataset(
        user=owner,
        owner_org=org["id"],
        private=False,
    )
    follower = factories.User()
    follow_context = {"user": follower["name"], "ignore_auth": False}

    # Follow it while it is still public.
    helpers.call_action("follow_dataset", follow_context, id=dataset["id"])
    followees = helpers.call_action(
        "followee_list", follow_context, id=follower["name"]
    )
    assert followees[0]["dict"]["id"] == dataset["id"]

    helpers.call_action(
        "package_patch",
        {"user": owner["name"], "ignore_auth": False},
        id=dataset["id"],
        private=True,
    )

    followees = helpers.call_action(
        "followee_list", follow_context, id=follower["name"]
    )
    assert len(followees) == 0


@pytest.mark.usefixtures("non_clean_db")
def test_followee_count_for_org_or_group():
    group = factories.Group(title="Finance")
    group2 = factories.Group(title="Environment")
    org = factories.Organization(title="Acme")

    user = factories.User()

    context = {"user": user["name"]}

    helpers.call_action("follow_group", context, id=group["id"])
    helpers.call_action("follow_group", context, id=group2["id"])
    helpers.call_action("follow_group", context, id=org["id"])

    group_followee_count = helpers.call_action(
        "group_followee_count", context, id=user["name"]
    )

    organization_followee_count = helpers.call_action(
        "organization_followee_count", context, id=user["name"]
    )

    assert group_followee_count == 2
    assert organization_followee_count == 1


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.parametrize("num_tokens", [0, 1, 2, 5])
def test_token_list(num_tokens):
    from ckan.lib.api_token import decode

    user = factories.User()
    ids = []
    for _ in range(num_tokens):
        data = helpers.call_action(
            "api_token_create",
            context={"model": model, "user": user["name"]},
            user=user["name"],
            name="token-name",
        )
        token = data["token"]
        ids.append(decode(token)["jti"])

    tokens = helpers.call_action(
        "api_token_list",
        context={"model": model, "user": user["name"]},
        user_id=user["name"],
    )
    assert sorted([t["id"] for t in tokens]) == sorted(ids)

    # Param "user" works for backwards compatibility
    tokens = helpers.call_action(
        "api_token_list",
        context={"model": model, "user": user["name"]},
        user=user["name"],
    )


@pytest.mark.usefixtures("non_clean_db")
def test_returned_if_sysadmin_and_include_plugin_extras_only():

    sysadmin = factories.Sysadmin()

    user = factories.User(plugin_extras={"plugin1": {"key1": "value1"}})

    context = {"user": sysadmin["name"], "ignore_auth": False}
    user = helpers.call_action(
        "user_show",
        context=context,
        id=user["id"],
        include_plugin_extras=True,
    )

    assert user["plugin_extras"] == {"plugin1": {"key1": "value1"}}

    context = {"user": sysadmin["name"], "ignore_auth": False}
    user = helpers.call_action("user_show", context=context, id=user["id"])

    assert "plugin_extras" not in user

    context = {"user": user["name"], "ignore_auth": False}
    user = helpers.call_action(
        "user_show",
        context=context,
        id=user["id"],
        include_plugin_extras=True,
    )

    assert "plugin_extras" not in user


@pytest.mark.usefixtures("non_clean_db")
def test_get_site_user_not_authorized(ckan_config):
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("get_site_user", {"model": model, "user": ""})

    assert helpers.call_auth(
        "get_site_user", {"model": model, "user": "", "ignore_auth": True}
    )


@pytest.mark.usefixtures("non_clean_db")
def test_user_patch_updating_single_field():
    user = factories.User(
        fullname="Mr. Test User",
        about="Just another test user.",
    )

    user = helpers.call_action(
        "user_patch",
        id=user["id"],
        about="somethingnew",
        context={"user": user["name"]},
    )

    assert user["fullname"] == "Mr. Test User"
    assert user["about"] == "somethingnew"

    user2 = helpers.call_action("user_show", id=user["id"])

    assert user2["fullname"] == "Mr. Test User"
    assert user2["about"] == "somethingnew"


@pytest.mark.usefixtures("non_clean_db")
def test_extensions_successful_patch_updating_user_name():
    user = factories.User()

    updated_user = helpers.call_action(
        "user_patch",
        context={"user": user["name"], "ignore_auth": True},
        id=user["id"],
        name="somethingnew",
    )

    assert updated_user["name"] == "somethingnew"

    user2 = helpers.call_action("user_show", id=user["id"])

    assert user2["name"] == "somethingnew"


@pytest.mark.usefixtures("non_clean_db")
def test_extensions_failed_patch_updating_user_name():
    user = factories.User()

    with pytest.raises(ValidationError):
        helpers.call_action(
            "user_patch",
            context={"user": user["name"], "ignore_auth": False},
            id=user["id"],
            name="somethingnew2",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_user_patch_sysadmin():

    sysadmin = factories.Sysadmin()
    user = factories.User()

    # cannot change your own sysadmin privs
    with pytest.raises(ValidationError):
        helpers.call_action(
            "user_patch",
            id=sysadmin["id"],
            sysadmin=False,
            context={"user": sysadmin["name"]},
        )

    # cannot change system user privs
    site_id = config.get("ckan.site_id")
    with pytest.raises(ValidationError) as e:
        helpers.call_action(
            "user_patch",
            id=site_id,
            sysadmin=False,
            context={"user": sysadmin["name"]},
        )
    assert e.value.error_dict["sysadmin"] == [
        "Cannot modify sysadmin privileges for system user"
    ]

    assert user["sysadmin"] is False

    helpers.call_action(
        "user_patch",
        id=user["id"],
        sysadmin=True,
        context={"user": sysadmin["name"]},
    )

    # user dicts do not have sysadmin key, get from db
    new_sysadmin = model.User.get(user["id"])

    assert new_sysadmin.sysadmin is True


@pytest.mark.usefixtures("non_clean_db")
class TestUpdateUser(object):
    def teardown(self):
        # Since some of the test methods below use the mock module to patch
        # things, we use this teardown() method to remove remove all patches.
        # (This makes sure the patches always get removed even if the test
        # method aborts with an exception or something.)
        mock.patch.stopall()

    def test_user_update_name(self):
        """Test that updating a user's name works successfully."""

        # The canonical form of a test has four steps:
        # 1. Setup any preconditions needed for the test.
        # 2. Call the function that's being tested, once only.
        # 3. Make assertions about the return value and/or side-effects of
        #    of the function that's being tested.
        # 4. Do nothing else!

        # 1. Setup.
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": False}
        user["name"] = "updated"

        # 2. Make assertions about the return value and/or side-effects.
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", context=context, **user)

    def test_user_update_with_id_that_does_not_exist(self):
        user_dict = vars(factories.User.stub())
        user_dict["id"] = "there's no user with this id"

        with pytest.raises(logic.NotFound):
            helpers.call_action("user_update", **user_dict)

    def test_user_update_with_no_id(self):
        user_dict = vars(factories.User.stub())
        assert "id" not in user_dict
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user_dict)

    @pytest.mark.parametrize(
        "name",
        (
            "",
            "a",
            False,
            0,
            -1,
            23,
            "new",
            "edit",
            "search",
            "a" * 200,
            "Hi!",
            "i++%",
        ),
    )
    def test_user_update_with_invalid_name(self, name):
        user = factories.User()
        user["name"] = name
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user)

    def test_user_update_to_name_that_already_exists(self):
        fred = factories.User()
        bob = factories.User()

        # Try to update fred and change his user name to bob, which is already
        # bob's user name
        fred["name"] = bob["name"]
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **fred)

    def test_user_update_password(self):
        """Test that updating a user's password works successfully."""

        user = factories.User()

        # FIXME we have to pass the email address to user_update even though
        # we're not updating it, otherwise validation fails.
        helpers.call_action(
            "user_update",
            id=user["id"],
            name=user["name"],
            email=user["email"],
            password="new password",
        )

        # user_show() never returns the user's password, so we have to access
        # the model directly to test it.
        import ckan.model as model

        updated_user = model.User.get(user["id"])
        assert updated_user.validate_password("new password")

    def test_user_update_with_short_password(self):
        user = factories.User()

        user["password"] = "xxx"  # This password is too short.
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user)

    def test_user_update_with_empty_password(self):
        """If an empty password is passed to user_update, nothing should
        happen.

        No error (e.g. a validation error) is raised, but the password is not
        changed either.

        """
        user_dict = vars(factories.User.stub())
        original_password = user_dict["password"]
        user_dict = factories.User(**user_dict)

        user_dict["password"] = ""
        helpers.call_action("user_update", **user_dict)

        import ckan.model as model

        updated_user = model.User.get(user_dict["id"])
        assert updated_user.validate_password(original_password)

    def test_user_update_with_null_password(self):
        user = factories.User()

        user["password"] = None
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user)

    def test_user_update_with_invalid_password(self):
        user = factories.User()

        for password in (False, -1, 23, 30.7):
            user["password"] = password
            with pytest.raises(logic.ValidationError):
                helpers.call_action("user_update", **user)

    def test_user_update_without_email_address(self):
        """You have to pass an email address when you call user_update.

        Even if you don't want to change the user's email address, you still
        have to pass their current email address to user_update.

        FIXME: The point of this feature seems to be to prevent people from
        removing email addresses from user accounts, but making them post the
        current email address every time they post to user update is just
        annoying, they should be able to post a dict with no 'email' key to
        user_update and it should simply not change the current email.

        """
        user = factories.User()
        del user["email"]

        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user)

    def test_user_update_with_custom_schema(self):
        """Test that custom schemas passed to user_update do get used.

        user_update allows a custom validation schema to be passed to it in the
        context dict. This is just a simple test that if you pass a custom
        schema user_update does at least call a custom method that's given in
        the custom schema. We assume this means it did use the custom schema
        instead of the default one for validation, so user_update's custom
        schema feature does work.

        """
        import ckan.logic.schema

        user = factories.User()

        # A mock validator method, it doesn't do anything but it records what
        # params it gets called with and how many times. We are using function
        # instead of MagicMock, because validator must have __code__ attribute
        calls = []

        def mock_validator(v):
            calls.append(v)
            return v

        # Build a custom schema by taking the default schema and adding our
        # mock method to its 'id' field.
        schema = ckan.logic.schema.default_update_user_schema()
        schema["id"].append(mock_validator)

        # Call user_update and pass our custom schema in the context.
        # FIXME: We have to pass email and password even though we're not
        # trying to update them, or validation fails.
        helpers.call_action(
            "user_update",
            context={"schema": schema},
            id=user["id"],
            name=user["name"],
            email=user["email"],
            password=factories.User.stub().password,
            fullname="updated full name",
        )
        assert calls == [user["id"]]

    def test_user_update_multiple(self):
        """Test that updating multiple user attributes at once works."""

        user = factories.User()

        params = {
            "id": user["id"],
            "fullname": "updated full name",
            "about": "updated about",
            # FIXME: We shouldn't have to put email here since we're not
            # updating it, but user_update sucks.
            "email": user["email"],
            # FIXME: We shouldn't have to put password here since we're not
            # updating it, but user_update sucks.
            "password": factories.User.stub().password,
        }

        helpers.call_action("user_update", **params)

        updated_user = helpers.call_action("user_show", id=user["id"])
        assert updated_user["fullname"] == "updated full name"
        assert updated_user["about"] == "updated about"

    def test_user_update_does_not_return_password(self):
        """The user dict that user_update returns should not include the user's
        password."""

        user = factories.User()

        params = {
            "id": user["id"],
            "fullname": "updated full name",
            "about": "updated about",
            "email": user["email"],
            "password": factories.User.stub().password,
        }

        updated_user = helpers.call_action("user_update", **params)
        assert "password" not in updated_user

    def test_user_update_does_not_return_reset_key(self):
        """The user dict that user_update returns should not include the user's
        reset key."""

        import ckan.lib.mailer
        import ckan.model

        user = factories.User()
        ckan.lib.mailer.create_reset_key(ckan.model.User.get(user["id"]))

        params = {
            "id": user["id"],
            "fullname": "updated full name",
            "about": "updated about",
            "email": user["email"],
            "password": factories.User.stub().password,
        }

        updated_user = helpers.call_action("user_update", **params)
        assert "reset_key" not in updated_user

    def test_normal_user_can_not_change_their_state(self):

        user = factories.User(state="pending")

        user["state"] = "active"

        updated_user = helpers.call_action("user_update", **user)

        updated_user["state"] == "pending"

    def test_sysadmin_user_can_change_a_user_state(self):

        user = factories.User(state="pending")
        sysadmin = factories.Sysadmin()

        user["state"] = "active"

        context = {"user": sysadmin["name"]}

        updated_user = helpers.call_action("user_update", context=context, **user)

        updated_user["state"] == "active"


@pytest.mark.usefixtures("non_clean_db")
def test_user_update_with_password_hash():
    sysadmin = factories.Sysadmin()
    context = {"user": sysadmin["name"]}

    user = helpers.call_action(
        "user_update",
        context=context,
        email=sysadmin["email"],
        id=sysadmin["name"],
        password_hash="pretend-this-is-a-valid-hash",
    )

    user_obj = model.User.get(user["id"])
    assert user_obj.password == "pretend-this-is-a-valid-hash"


@pytest.mark.usefixtures("non_clean_db")
def test_userupdate_user_create_password_hash_not_for_normal_users():
    normal_user = factories.User()
    context = {"user": normal_user["name"], "ignore_auth": False}

    user = helpers.call_action(
        "user_update",
        context=context,
        email=normal_user["email"],
        id=normal_user["name"],
        password="required",
        password_hash="pretend-this-is-a-valid-hash",
    )

    user_obj = model.User.get(user["id"])
    assert user_obj.password != "pretend-this-is-a-valid-hash"


@pytest.mark.usefixtures("non_clean_db")
def test_user_update_image_url():
    user = factories.User(image_url="user_image.jpg")
    context = {"user": user["name"]}

    user = helpers.call_action(
        "user_update",
        context=context,
        id=user["name"],
        email=user["email"],
        image_url="new_image_url.jpg",
    )

    assert user["image_url"] == "new_image_url.jpg"


@pytest.mark.usefixtures("non_clean_db")
def test_stored_on_update_if_sysadmin():

    sysadmin = factories.Sysadmin()

    user = factories.User(plugin_extras={"plugin1": {"key1": "value1"}})

    user["plugin_extras"] = {"plugin1": {"key1": "value1.2", "key2": "value2"}}

    # helpers.call_action sets 'ignore_auth' to True by default
    context = {"user": sysadmin["name"], "ignore_auth": False}

    updated_user = helpers.call_action("user_update", context=context, **user)

    assert updated_user["plugin_extras"] == {
        "plugin1": {
            "key1": "value1.2",
            "key2": "value2",
        }
    }

    context = {"user": sysadmin["name"], "ignore_auth": False}
    user = helpers.call_action(
        "user_show",
        context=context,
        id=user["id"],
        include_plugin_extras=True,
    )

    assert updated_user["plugin_extras"] == {
        "plugin1": {
            "key1": "value1.2",
            "key2": "value2",
        }
    }

    plugin_extras_from_db = model.Session.execute(
        sa.text('SELECT plugin_extras FROM "user" WHERE id=:id'),
        {"id": user["id"]},
    ).first()[0]

    assert plugin_extras_from_db == {
        "plugin1": {
            "key1": "value1.2",
            "key2": "value2",
        }
    }


@pytest.mark.usefixtures("non_clean_db")
def test_ignored_on_update_if_non_sysadmin():

    sysadmin = factories.Sysadmin()

    user = factories.User(plugin_extras={"plugin1": {"key1": "value1"}})

    user["plugin_extras"] = {"plugin1": {"key1": "value1.2", "key2": "value2"}}

    # User edits themselves
    context = {"user": user["name"], "ignore_auth": False}

    created_user = helpers.call_action("user_update", context=context, **user)

    assert "plugin_extras" not in created_user

    context = {"user": sysadmin["name"], "ignore_auth": False}
    user = helpers.call_action(
        "user_show",
        context=context,
        id=created_user["id"],
        include_plugin_extras=True,
    )

    assert user["plugin_extras"] == {"plugin1": {"key1": "value1"}}


@pytest.mark.usefixtures("non_clean_db")
def test_ignored_on_update_if_non_sysadmin_when_empty():

    sysadmin = factories.Sysadmin()

    user = factories.User()

    user["plugin_extras"] = {"plugin1": {"key1": "value1.2", "key2": "value2"}}

    # User edits themselves
    context = {"user": user["name"], "ignore_auth": False}

    created_user = helpers.call_action("user_update", context=context, **user)

    assert "plugin_extras" not in created_user

    context = {"user": sysadmin["name"], "ignore_auth": False}
    user = helpers.call_action(
        "user_show",
        context=context,
        id=created_user["id"],
        include_plugin_extras=True,
    )

    assert user["plugin_extras"] is None


@pytest.mark.usefixtures("non_clean_db")
def test_nested_updates_are_reflected_in_db():

    user = factories.User(plugin_extras={"plugin1": {"key1": "value1"}})

    sysadmin = factories.Sysadmin()

    context = {"user": sysadmin["name"]}

    user = helpers.call_action(
        "user_show",
        context=context,
        id=user["id"],
        include_plugin_extras=True,
    )

    user["plugin_extras"]["plugin1"]["key1"] = "value2"

    updated_user = helpers.call_action("user_update", context=context, **user)

    assert updated_user["plugin_extras"]["plugin1"]["key1"] == "value2"

    # Hold on, partner

    plugin_extras = model.Session.execute(
        sa.text('SELECT plugin_extras FROM "user" WHERE id=:id'),
        {"id": user["id"]},
    ).first()[0]

    assert plugin_extras["plugin1"]["key1"] == "value2"
