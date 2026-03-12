from __future__ import annotations
from typing import Any
import pytest
from faker import Faker

from ckan import types
from ckan.lib.api_token import encode_token


class TestDownload:
    def test_download_content(
        self,
        api_token_factory: types.TestFactory,
        file_factory: types.TestFactory,
        faker: Faker,
        app: types.FixtureApp,
    ):
        """Test downloading a file with correct authorization."""
        content = faker.binary(100)
        file = file_factory(upload=content)

        resp = app.get(f"/file/download/{file['id']}")
        assert resp.status_code == 404

        token = api_token_factory(user=file["owner_id"])
        resp = app.get(
            f"/file/download/{file['id']}", headers={"Authorization": token["token"]}
        )

        assert resp.status_code == 200
        assert resp.data == content


class TestPublicDownload:
    @pytest.mark.ckan_config(
        "ckan.files.storage.non_public_storage.type", "ckan:memory"
    )
    def test_public_download_from_non_public_storage(
        self,
        file_factory: types.TestFactory,
        app: types.FixtureApp,
    ):
        """Test downloading a file from a non-public storage."""
        file = file_factory()

        resp = app.get(f"/file/public-download/non_public_storage/{file['location']}")
        assert resp.status_code == 403

    @pytest.mark.ckan_config("ckan.files.storage.public_storage.type", "ckan:memory")
    @pytest.mark.ckan_config("ckan.files.storage.public_storage.public", True)
    def test_public_download_from_public_storage(
        self, file_factory: types.TestFactory, app: types.FixtureApp, faker: Faker
    ):
        """Test downloading a file from a public storage, without authorization."""
        content = faker.binary(100)
        file = file_factory(upload=content, storage="public_storage")

        resp = app.get(f"/file/public-download/public_storage/{file['location']}")

        assert resp.status_code == 200
        assert resp.data == content


class TestTrustedDownload:
    def test_valid_token(
        self,
        file_factory: types.TestFactory,
        app: types.FixtureApp,
        faker: Faker,
    ):
        """Test downloading a file with a valid JWT token."""
        content = faker.binary(100)
        file = file_factory(upload=content)

        token = encode_token({"sub": file["id"], "aud": "trusted_download"})

        resp = app.get(f"/file/trusted-download/{token}")

        assert resp.status_code == 200
        assert resp.data == content

    def test_without_aud(self, app: types.FixtureApp, file: dict[str, Any]):
        """Test that a token without the correct audience is rejected."""
        token = encode_token({"sub": file["id"]})

        resp = app.get(f"/file/trusted-download/{token}")
        assert resp.status_code == 404

    def test_invalid_token(self, app: types.FixtureApp):
        """Test that an invalid token is rejected."""
        token = "invalid.token.value"

        resp = app.get(f"/file/trusted-download/{token}")
        assert resp.status_code == 404

    def test_expired_token(self, app: types.FixtureApp, file: dict[str, Any]):
        """Test that an expired token is rejected."""
        token = encode_token(
            {"sub": file["id"], "aud": "trusted_download", "exp": 1},
        )

        resp = app.get(f"/file/trusted-download/{token}")
        assert resp.status_code == 404

    def test_missing_file(self, app: types.FixtureApp):
        """Test that a valid token for a non-existing file returns 404."""
        token = encode_token({"sub": "non-existing-file-id", "aud": "trusted_download"})

        resp = app.get(f"/file/trusted-download/{token}")
        assert resp.status_code == 404

    def test_by_location(
        self, app: types.FixtureApp, file_factory: types.TestFactory, faker: Faker
    ):
        """Test downloading a file using a token with location and storage."""
        content = faker.binary(100)
        file = file_factory(upload=content)

        token = encode_token(
            {
                "storage": file["storage"],
                "location": file["location"],
                "aud": "trusted_download",
            }
        )

        resp = app.get(f"/file/trusted-download/{token}")

        assert resp.status_code == 200
        assert resp.data == content
