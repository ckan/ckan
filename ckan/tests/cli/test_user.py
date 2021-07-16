# -*- coding: utf-8 -*-

import pytest

import ckan.model as model
from ckan.tests.helpers import call_action
from ckan.cli.cli import ckan
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db")
class TestUserAdd(object):

    def test_cli_user_add_valid_args(self, cli):
        """Command shouldn't raise SystemExit when valid args are provided.
        """
        args = [
            "user",
            "add",
            "berty",
            "password=password123",
            "fullname=Berty Guffball",
            "email=berty@example.com",
        ]
        result = cli.invoke(ckan, args)

        assert result.exit_code == 0

    def test_cli_user_add_no_args(self, cli):
        """Command with no args raises SystemExit.
        """
        result = cli.invoke(ckan, ['user', 'add'])
        assert result.exit_code

    def test_cli_user_add_no_fullname(self, cli):
        """Command shouldn't raise SystemExit when fullname arg not present.
        """
        args = [
            "user",
            "add",
            "berty",
            "password=password123",
            "email=berty@example.com",
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code

    def test_cli_user_add_unicode_fullname_unicode_decode_error(self, cli):
        """
        Command shouldn't raise UnicodeDecodeError when fullname contains
        characters outside of the ascii characterset.
        """
        args = [
            "user",
            "add",
            "berty",
            "password=password123",
            "fullname=Harold Müffintøp",
            "email=berty@example.com",
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code

    def test_cli_user_add_unicode_fullname_system_exit(self, cli):
        """
        Command shouldn't raise SystemExit when fullname contains
        characters outside of the ascii characterset.
        """
        args = [
            "user",
            "add",
            "berty",
            "password=password123",
            "fullname=Harold Müffintøp",
            "email=berty@example.com",
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code


@pytest.mark.usefixtures("clean_db")
class TestApiToken(object):

    def test_revoke(self, cli):
        user = factories.User()
        call_action("api_token_create", user=user["id"], name="first token")
        tid = model.Session.query(model.ApiToken).first().id
        args = [
            "user",
            "token",
            "revoke",
            tid,
        ]
        result = cli.invoke(ckan, args)
        assert result.exit_code == 0
        assert "API Token has been revoked" in result.output

        result = cli.invoke(ckan, args)
        assert result.exit_code == 1
        assert "API Token not found" in result.output

    def test_list(self, cli):
        user = factories.User()
        call_action("api_token_create", user=user["id"], name="first token")
        call_action("api_token_create", user=user["id"], name="second token")
        args = [
            "user",
            "token",
            "list",
            user["name"],
        ]
        result = cli.invoke(ckan, args)
        assert result.exit_code == 0
        for (id,) in model.Session.query(model.ApiToken.id):
            assert id in result.output

    def test_add_with_extras(self, cli):
        """Command shouldn't raise SystemExit when valid args are provided.
        """
        user = factories.User()
        args = [
            "user",
            "token",
            "add",
            user["name"],
            "new_token",
            """--json={"x": "y"}""",
        ]

        assert model.Session.query(model.ApiToken).count() == 0
        result = cli.invoke(ckan, args)
        assert result.exit_code == 0
        assert model.Session.query(model.ApiToken).count() == 1

        args = [
            "user",
            "token",
            "add",
            user["name"],
            "new_token",
            "x=1",
            "y=2"
        ]

        result = cli.invoke(ckan, args)
        assert result.exit_code == 0
        assert model.Session.query(model.ApiToken).count() == 2

        args = [
            "user",
            "token",
            "add",
            user["name"],
            "new_token",
            "x",
            "y=2"
        ]

        result = cli.invoke(ckan, args)
        assert result.exit_code == 1
        assert model.Session.query(model.ApiToken).count() == 2
