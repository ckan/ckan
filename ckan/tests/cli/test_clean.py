from __future__ import annotations

import pytest
from typing import Any
from ckan.cli.cli import ckan
from ckan.tests.helpers import call_action


@pytest.fixture
def with_temporal_storage(
    reset_storages: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmpdir: Any,
    ckan_config: dict[str, Any],
):
    name = ckan_config["ckan.files.default_storages.default"]
    monkeypatch.setitem(ckan_config, f"ckan.files.storage.{name}.type", "ckan:fs")
    monkeypatch.setitem(ckan_config, f"ckan.files.storage.{name}.path", tmpdir)
    reset_storages()


@pytest.mark.usefixtures("clean_db", "with_extended_cli", "with_temporal_storage")
@pytest.mark.ckan_config("ckan.upload.user.mimetypes", "*")
@pytest.mark.ckan_config("ckan.upload.user.types", "*")
class TestUserClean:
    def test_output_if_there_are_not_invalid_users(self, cli):
        result = cli.invoke(ckan, ["clean", "users"])
        assert "No users were found with invalid images." in result.output

    def test_confirm_dialog_if_no_force(
            self, cli, monkeypatch, create_with_upload, faker, ckan_config, reset_storages
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
            ckan_config, "ckan.files.storage.test.supported_types", "image/png"
        )
        reset_storages()
        result = cli.invoke(ckan, ["clean", "users"])

        assert (
            f"User {fake_user['name']} has an invalid image:"
            f" {fake_user['image_url']}"
            in result.output
        )
        assert (
            f"User {user['name']} has an invalid image: {user['image_url']}"
            not in result.output
        )
        assert "Permanently delete users and their images?" in result.output
        users = call_action("user_list")
        assert len(users) == 2

    def test_correct_users_are_deleted(
            self, cli, monkeypatch, create_with_upload, faker, ckan_config, reset_storages
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
            ckan_config, "ckan.files.storage.test.supported_types", "image/png"
        )
        reset_storages()

        result = cli.invoke(ckan, ["clean", "users", "--force"])
        users = call_action("user_list")
        assert f"Deleted user: {fake_user['name']}" in result.output
        assert len(users) == 1
        assert users[0]["name"] == "valid-user"
