# -*- coding: utf-8 -*-

import pytest

import ckan.model as model
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

        # tid must be escaped. When it starts with a hyphen it treated as a
        # flag otherwise.
        args = f'user token revoke "{tid}"'
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


@pytest.mark.usefixtures("clean_db")
class TestUserClean():

    def test_output_if_there_are_not_invalid_users(self, cli):
        result = cli.invoke(ckan, ["user", "clean"])
        assert "No users were found with invalid images." in result.output

    @pytest.mark.ckan_config("ckan.upload.user.mimetypes", "")
    @pytest.mark.ckan_config("ckan.upload.user.types", "")
    def test_confirm_dialog_if_no_force(self, cli, monkeypatch, create_with_upload, faker, ckan_config):
        fake_user = {
            "name": "fake-user",
            "email": "fake-user@example.com",
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        fake_user = create_with_upload("<html><body>hello world</body></html>", "index.html", **fake_user)

        user = {
            "name": "valid-user",
            "email": "valid-user@example",
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        user = create_with_upload(faker.image(), "image.png", **user)

        monkeypatch.setitem(ckan_config, "ckan.upload.user.mimetypes", "image/png")
        result = cli.invoke(ckan, ["user", "clean"])

        assert f"User {fake_user['name']} has an invalid image: {fake_user['image_url']}" in result.output
        assert f"User {user['name']} has an invalid image: {user['image_url']}" not in result.output
        assert "Delete users and its images?" in result.output
        users = call_action("user_list")
        assert len(users) == 2

    @pytest.mark.ckan_config("ckan.upload.user.mimetypes", "")
    @pytest.mark.ckan_config("ckan.upload.user.types", "")
    def test_correct_users_are_deleted(self, cli, monkeypatch, create_with_upload, faker, ckan_config):
        fake_user = {
            "name": "fake-user",
            "email": "fake-user@example.com",
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        fake_user = create_with_upload("<html><body>hello world</body></html>", "index.html", **fake_user)

        user = {
            "name": "valid-user",
            "email": "valid-user@example",
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        user = create_with_upload(faker.image(), "image.png", **user)

        monkeypatch.setitem(ckan_config, "ckan.upload.user.mimetypes", "image/png")
        result = cli.invoke(ckan, ["user", "clean", "--force"])
        users = call_action("user_list")
        assert f"User {fake_user['name']} with image ({fake_user['image_url']}) has been deleted." in result.output
        assert len(users) == 1
        assert users[0]["name"] == "valid-user"
