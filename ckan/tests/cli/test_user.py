# -*- coding: utf-8 -*-

import pytest

from unittest import mock

import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.lib.mailer as mailer

from ckan.tests.helpers import call_action
from ckan.cli.cli import ckan
from ckan.tests import factories


@pytest.mark.usefixtures("non_clean_db")
class TestUserAdd(object):

    def test_cli_user_add_valid_args(self, cli):
        """Command shouldn't raise SystemExit when valid args are provided.
        """
        args = [
            u"user",
            u"add",
            factories.User.stub().name,
            u"password=password123",
            u"fullname=Berty Guffball",
            u"email=" + factories.User.stub().email,
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code, result.output

    def test_cli_user_add_no_args(self, cli):
        """Command with no args raises SystemExit.
        """
        result = cli.invoke(ckan, [u'user', u'add'])
        assert result.exit_code

    def test_cli_user_add_no_fullname(self, cli):
        """Command shouldn't raise SystemExit when fullname arg not present.
        """
        args = [
            u"user",
            u"add",
            factories.User.stub().name,
            u"password=password123",
            u"email=" + factories.User.stub().email,
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code, result.output

    def test_cli_user_add_unicode_fullname_unicode_decode_error(self, cli):
        """
        Command shouldn't raise UnicodeDecodeError when fullname contains
        characters outside of the ascii characterset.
        """
        args = [
            u"user",
            u"add",
            factories.User.stub().name,
            u"password=password123",
            u"fullname=Harold Müffintøp",
            u"email=" + factories.User.stub().email,
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code, result.output

    def test_cli_user_add_unicode_fullname_system_exit(self, cli):
        """
        Command shouldn't raise SystemExit when fullname contains
        characters outside of the ascii characterset.
        """
        args = [
            u"user",
            u"add",
            factories.User.stub().name,
            u"password=password123",
            u"fullname=Harold Müffintøp",
            u"email=" + factories.User.stub().email,
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code, result.output


@pytest.mark.usefixtures(u"non_clean_db")
class TestApiToken(object):

    def test_revoke(self, cli):
        user = factories.User()
        call_action(u"api_token_create", user=user[u"id"], name=u"first token")
        tid = model.Session.query(model.ApiToken).first().id

        # tid must be prefixed by --. When it starts with a hyphen it treated
        # as a flag otherwise.
        args = ["user", "token", "revoke", "--", tid]
        result = cli.invoke(ckan, args)
        assert not result.exit_code, result.output
        assert u"API Token has been revoked" in result.output

        result = cli.invoke(ckan, args)
        assert result.exit_code == 1
        assert u"API Token not found" in result.output

    def test_list(self, cli):
        user = factories.User()
        call_action(u"api_token_create", user=user[u"id"], name=u"first token")
        call_action(u"api_token_create", user=user[u"id"], name=u"second token")
        args = [
            u"user",
            u"token",
            u"list",
            user[u"name"],
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code, result.output
        tokens = model.Session.query(model.ApiToken.id).filter_by(
            user_id=user["id"])
        assert all(token.id in result.output for token in tokens)

    def test_add_with_extras(self, cli):
        """Command shouldn't raise SystemExit when valid args are provided.
        """
        user = factories.User()
        args = [
            u"user",
            u"token",
            u"add",
            user[u"name"],
            u"new_token",
            u"""--json={"x": "y"}""",
        ]

        initial = model.Session.query(model.ApiToken).count()
        result = cli.invoke(ckan, args)
        assert not result.exit_code, result.output
        assert model.Session.query(model.ApiToken).count() == initial + 1

        args = [
            u"user",
            u"token",
            u"add",
            user[u"name"],
            u"new_token",
            u"x=1",
            u"y=2"
        ]

        result = cli.invoke(ckan, args)
        assert not result.exit_code, result.output
        assert model.Session.query(model.ApiToken).count() == initial + 2

        args = [
            u"user",
            u"token",
            u"add",
            user[u"name"],
            u"new_token",
            u"x",
            u"y=2"
        ]

        result = cli.invoke(ckan, args)
        assert result.exit_code == 1
        assert model.Session.query(model.ApiToken).count() == initial + 2


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestUserResendInvite:

    def test_resend_invite_specific_user(self, cli, mail_server):
        org = factories.Organization()

        data_dict = {
            "email": "test@example.com",
            "group_id": org["id"],
            "role": "member",
        }
        with mock.patch(
            "ckan.lib.mailer.mail_user",
            side_effect=mailer.MailerException("Simulated failure"),
        ):
            with pytest.raises(tk.ValidationError):
                call_action("user_invite", **data_dict)

        args = ["user", "resend-invite", "--user-email", "test@example.com"]
        result = cli.invoke(ckan, args)
        assert not result.exit_code, result.output

        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1

        _, _, to_addrs, msg = msgs[0]
        assert to_addrs == ["test@example.com"]
        assert "Invite for CKAN" in msg

    def test_resend_invite_non_existent_user(self, cli):
        args = [
            "user",
            "resend-invite",
            "--user-email",
            "nonexistent@example.com",
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code
        msg = "User with email 'nonexistent@example.com' not found."
        assert msg in result.output

    def test_resend_invite_no_pending_invitations(self, cli):
        args = [
            "user",
            "resend-invite",
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code, result.output
        assert "No pending user invitations found to resend." in result.output

    def test_resend_invite_multiple_users(self, cli, mail_server):
        org = factories.Organization()

        users_data = [
            {
                "email": "user1@example.com",
                "group_id": org["id"],
                "role": "member",
            },
            {
                "email": "user2@example.com",
                "group_id": org["id"],
                "role": "editor",
            },
            {
                "email": "user3@example.com",
                "group_id": org["id"],
                "role": "admin",
            },
        ]
        for user_data in users_data:
            with mock.patch(
                "ckan.lib.mailer.mail_user",
                side_effect=mailer.MailerException("Simulated failure"),
            ):
                with pytest.raises(tk.ValidationError):
                    call_action("user_invite", **user_data)

        args = [
            "user",
            "resend-invite",
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code, result.output

        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == len(users_data)

        for i, user_data in enumerate(users_data):
            _, _, to_addrs, msg = msgs[i]
            assert to_addrs == [user_data["email"]]
            assert "Invite for CKAN" in msg
