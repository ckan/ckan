# -*- coding: utf-8 -*-
import pytest
import six

from ckan.cli.cli import ckan
from ckan.tests.helpers import call_action


@pytest.mark.skipif(six.PY2, reason="Faker image tests don't work on PY2")
@pytest.mark.usefixtures("clean_db")
class TestUserClean:
    @pytest.mark.ckan_config("ckan.upload.user.mimetypes", "image/png")
    @pytest.mark.ckan_config("ckan.upload.user.types", "images")
    def test_output_if_there_are_not_invalid_users(self, cli):
        result = cli.invoke(ckan, ["clean", "users"])
        assert "No users were found with invalid images." in result.output

    @pytest.mark.ckan_config("ckan.upload.user.mimetypes", "")
    @pytest.mark.ckan_config("ckan.upload.user.types", "")
    def test_confirm_dialog_if_no_force(
        self, cli, monkeypatch, create_with_upload, faker, ckan_config
    ):
        fake_user = {
            "name": "fake-user",
            "email": "fake-user@example.com",
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        fake_user = create_with_upload(
            "<html><body>hello world</body></html>", "index.html", **fake_user
        )

        user = {
            "name": "valid-user",
            "email": "valid-user@example",
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        user = create_with_upload(faker.image(), "image.png", **user)

        monkeypatch.setitem(
            ckan_config, "ckan.upload.user.mimetypes", "image/png"
        )
        result = cli.invoke(ckan, ["clean", "users"])

        assert (
            "User {} has an invalid image: {}".format(fake_user['name'], fake_user['image_url'])
            in result.output
        )
        assert (
            "User {} has an invalid image: {}".format(user['name'], user['image_url'])
            not in result.output
        )
        assert "Permanently delete users and their images?" in result.output
        users = call_action("user_list")
        assert len(users) == 2

    @pytest.mark.ckan_config("ckan.upload.user.mimetypes", "")
    @pytest.mark.ckan_config("ckan.upload.user.types", "")
    def test_correct_users_are_deleted(
        self, cli, monkeypatch, create_with_upload, faker, ckan_config
    ):
        fake_user = {
            "name": "fake-user",
            "email": "fake-user@example.com",
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        fake_user = create_with_upload(
            "<html><body>hello world</body></html>", "index.html", **fake_user
        )

        user = {
            "name": "valid-user",
            "email": "valid-user@example",
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        user = create_with_upload(faker.image(), "image.png", **user)

        monkeypatch.setitem(
            ckan_config, "ckan.upload.user.mimetypes", "image/png"
        )
        result = cli.invoke(ckan, ["clean", "users", "--force"])
        users = call_action("user_list")
        assert "Deleted user: {}".format(fake_user['name']) in result.output
        assert len(users) == 1
        assert users[0]["name"] == "valid-user"
