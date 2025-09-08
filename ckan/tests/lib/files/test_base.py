from __future__ import annotations

import pytest
from faker import Faker
from typing import Iterable, Any

from ckan.lib import files
from ckan.lib.files import base


@pytest.mark.parametrize(
    ("type", "supported", "outcome"),
    [
        ("text/csv", ["csv"], True),
        ("text/csv", ["json", "text"], True),
        ("text/csv", ["application/json", "text/plain", "text/csv", "image/png"], True),
        ("text/csv", ["json", "image"], False),
        ("text/csv", ["application/csv"], False),
        ("text/csv", ["text/plain"], False),
        ("text/csv", ["non-csv"], False),
    ],
)
def test_is_supported_type(type: str, supported: Iterable[str], outcome: bool):
    assert base.is_supported_type(type, supported) is outcome


class TestStorage:
    def test_validate_size(self):
        """Size validation depends on settings."""
        storage = base.Storage({})
        storage.validate_size(999_999_999_999_999_999_999)

        storage = base.Storage({"max_size": 10})
        storage.validate_size(9)
        storage.validate_size(10)
        with pytest.raises(files.exc.LargeUploadError):
            storage.validate_size(11)

    def test_validate_content_type(self):
        """Type validation depends on settings."""
        storage = base.Storage({})
        storage.validate_content_type("text/csv")

        storage = base.Storage({"supported_types": ["text", "json", "image/png"]})
        storage.validate_content_type("text/csv")
        storage.validate_content_type("application/json")
        storage.validate_content_type("image/png")

        with pytest.raises(files.exc.WrongUploadTypeError):
            storage.validate_content_type("image/jpeg")

        with pytest.raises(files.exc.WrongUploadTypeError):
            storage.validate_content_type("application/pdf")

        with pytest.raises(files.exc.WrongUploadTypeError):
            storage.validate_content_type("binary/csv")

    @pytest.mark.ckan_config("ckan.files.storage.test.type", "ckan:null")
    def test_as_response(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ckan_config: dict[str, Any],
        faker: Faker,
        reset_storages: Any,
    ):
        reset_storages()

        storage = files.get_storage("test")
        assert isinstance(storage, base.Storage)

        name = faker.file_name()
        size = faker.pyint()
        info = files.FileData(files.Location(name), content_type="image/png", size=size)

        resp = storage.as_response(info)

        assert resp.headers["Content-length"] == str(info.size)
        assert resp.headers["Content-type"] == info.content_type
        assert resp.headers["Content-disposition"] == f"attachment; filename={name}"

        monkeypatch.setitem(ckan_config, "ckan.files.inline_content_types", ["image"])
        resp = storage.as_response(info)
        assert resp.headers["Content-disposition"] == f"inline; filename={name}"
