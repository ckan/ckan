from __future__ import annotations

from faker import Faker

from ckan import types


class TestDownload:
    def test_download_content(
        self,
        api_token_factory: types.TestFactory,
        file_factory: types.TestFactory,
        faker: Faker,
        app: types.FixtureApp,
    ):
        """Test downloading a file with proper authorization."""
        content = faker.binary(100)
        file = file_factory(upload=content)

        resp = app.get(f"/file/download/{file['id']}")
        assert resp.status_code == 403

        token = api_token_factory(user=file["owner_id"])
        resp = app.get(
            f"/file/download/{file['id']}", headers={"Authorization": token["token"]}
        )

        assert resp.status_code == 200
        assert resp.data == content
