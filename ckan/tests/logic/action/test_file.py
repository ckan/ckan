from __future__ import annotations

import io
import uuid
from typing import Any

import pytest
import sqlalchemy as sa
from faker import Faker
from werkzeug.datastructures import FileStorage

import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan import types
from ckan.tests.factories import fake
from ckan.tests.helpers import call_action

call_action: Any


class TestFileCreate:
    def test_unknown_storage(self, file_factory: types.TestFactory, faker: Faker):
        """Unknown storage produces an error."""
        with pytest.raises(tk.ValidationError):
            file_factory(storage=faker.word())

    @pytest.mark.ckan_config(
        "ckan.files.storage.test.disabled_capabilities", ["CREATE"]
    )
    def test_missing_create_capability(self, file_factory: types.TestFactory):
        """Missing CREATE capability is reported via validation error."""
        with pytest.raises(tk.ValidationError):
            file_factory()

    def test_name_explicit(self, file_factory: types.TestFactory):
        """Name can be overriden even when upload contains filename."""
        name = fake.unique.file_name()
        ignored_name = fake.unique.file_name()
        upload = FileStorage(io.BytesIO(fake.binary(100)), ignored_name)
        result = file_factory(name=name, upload=upload)
        assert result["location"] == name

    def test_missing_name(self, file_factory: types.TestFactory, faker: Faker):
        """If upload does not have filename, explicit name is required."""
        with pytest.raises(tk.ValidationError):
            file_factory(upload=faker.binary(100), name=None)

    def test_name_deduced_from_file(self, file_factory: types.TestFactory):
        """If upload contains filename, explicit name is not required."""
        name = fake.unique.file_name()
        upload = FileStorage(io.BytesIO(fake.binary(100)), name)
        result = file_factory(upload=upload, name=None)
        assert result["location"] == name

    def test_name_secured(self, file_factory: types.TestFactory):
        """Filename is sanitized even without location transformers."""
        bad_name = fake.unique.file_path()
        good_name = bad_name.lstrip("/").replace("/", "_")

        result = file_factory(name=bad_name)
        assert result["location"] == good_name

    @pytest.mark.ckan_config(
        "ckan.files.storage.test.location_transformers", ["uuid_prefix"]
    )
    def test_location_transformed(self, file_factory: types.TestFactory):
        """Location transformers are applied to the location."""
        name = fake.unique.file_name()
        result = file_factory(name=name)

        prefix = result["location"][: -len(name)]
        assert uuid.UUID(prefix)

        suffix = result["location"][-len(name) :]
        assert suffix == name

    def test_existing(self, file: dict[str, Any], file_factory: types.TestFactory):
        """Existing file reported via validation error."""
        with pytest.raises(tk.ValidationError):
            file_factory(name=file["location"])

    @pytest.mark.ckan_config("ckan.files.storage.test.override_existing", True)
    def test_override_does_not_allow_rewriting_file(
        self, file: dict[str, Any], file_factory: types.TestFactory
    ):
        """Even with enabled overrides, file is not replaced during creation."""
        with pytest.raises(tk.ValidationError):
            file_factory(name=file["location"])

    def test_owner(self, file_factory: types.TestFactory, user: dict[str, Any]):
        """Owner set to the current user."""
        file = file_factory(user="")
        assert file["owner_id"] is None
        assert file["owner_type"] is None

        file = file_factory(user=user)
        assert file["owner_id"] == user["id"]
        assert file["owner_type"] == "user"


class TestFileSearch: ...


class TestFileDelete:
    def test_delete_missing(self, faker: Faker):
        """Attempt to remove non-existing file causes an error."""
        with pytest.raises(tk.NotFound):
            call_action("file_delete", id=faker.uuid4())

    @pytest.mark.ckan_config(
        "ckan.files.storage.test.disabled_capabilities", ["REMOVE"]
    )
    def test_missing_remove_capability(
        self,
        file: dict[str, Any],
    ):
        """Missing REMOVE capability is reported via validation error."""
        with pytest.raises(tk.ValidationError):
            call_action("file_delete", id=file["id"])

    def test_delete_real(self, file: dict[str, Any]):
        """File can be removed."""
        call_action("file_delete", id=file["id"])
        existing = model.Session.get(model.File, file["id"])
        assert not existing


class TestFileShow:
    def test_show_missing(self, faker: Faker):
        """Attempt to show non-existing file causes an error."""
        with pytest.raises(tk.NotFound):
            call_action("file_show", id=faker.uuid4())

    def test_show_real(self, file: dict[str, Any]):
        """Real file can be shown."""
        result = call_action("file_show", id=file["id"])
        assert result == file


class TestFileRename:
    def test_rename_missing(self, faker: Faker):
        """Attempt to rename non-existing file causes an error."""
        with pytest.raises(tk.NotFound):
            call_action("file_rename", id=faker.uuid4(), name=faker.file_name())

    def test_rename_real(self, faker: Faker, file: dict[str, Any]):
        """Real file can be renamed."""
        name = faker.file_name()
        result = call_action("file_rename", id=file["id"], name=name)

        assert result["name"] == name
        assert result["location"] == file["location"]
        assert result["id"] == file["id"]

    def test_name_secured(self, file: dict[str, Any]):
        """Filename is sanitized."""
        bad_name = fake.unique.file_path()
        good_name = bad_name.lstrip("/").replace("/", "_")

        result = call_action("file_rename", id=file["id"], name=bad_name)

        assert result["name"] == good_name


class TestFilePin:
    def test_pin_missing(self, faker: Faker):
        """Attempt to pin non-existing file causes an error."""
        with pytest.raises(tk.NotFound):
            call_action("file_pin", id=faker.uuid4())

    def test_pin_unowned(self, file_factory: types.TestFactory):
        """Attempt to pin unowned file causes an error."""
        file = file_factory(user="")
        with pytest.raises(tk.ValidationError):
            call_action("file_pin", id=file["id"])

    def test_pin_real(self, file: dict[str, Any]):
        """Real file can be pinned."""
        result = call_action("file_pin", id=file["id"])
        assert result["pinned"]


class TestFileUnpin:
    def test_unpin_missing(self, faker: Faker):
        """Attempt to unpin non-existing file causes an error."""
        with pytest.raises(tk.NotFound):
            call_action("file_unpin", id=faker.uuid4())

    def test_unpin_unowned(self, file_factory: types.TestFactory):
        """Unowned file can be unpinned(nothing is changed)."""
        file = file_factory(user="")
        result = call_action("file_unpin", id=file["id"])
        assert not result["pinned"]

    def test_unpin_real(self, file: dict[str, Any]):
        """Real file can be unpinned."""
        result = call_action("file_unpin", id=file["id"])
        assert not result["pinned"]


class TestFileOwnershipTransfer:
    def test_transfer_missing(self, faker: Faker):
        """Attempt to transfer non-existing file causes an error."""
        with pytest.raises(tk.NotFound):
            call_action(
                "file_ownership_transfer",
                id=faker.uuid4(),
                owner_id=fake.unique.uuid4(),
                owner_type="user",
            )

    def test_transfer_pinned(self, faker: Faker, file: dict[str, Any]):
        """Attempt to transfer pinned file causes an error without force-flag."""
        call_action("file_pin", id=file["id"])
        new_owner = faker.uuid4()
        with pytest.raises(tk.ValidationError):
            call_action(
                "file_ownership_transfer",
                id=file["id"],
                owner_id=new_owner,
                owner_type="user",
            )

        result = call_action(
            "file_ownership_transfer",
            id=file["id"],
            owner_id=new_owner,
            owner_type="user",
            force=True,
        )
        assert result["owner_id"] == new_owner

    def test_transfer_history(
        self, faker: Faker, file_factory: types.TestFactory[model.File]
    ):
        """Transfer history is recorded when owner changes."""
        fileobj = file_factory.model()

        assert fileobj.owner
        stmt = fileobj.owner.select_history().with_only_columns(sa.func.count())
        size = model.Session.scalar(stmt)
        assert not size

        # owner remains the same, history is not recorded
        call_action(
            "file_ownership_transfer",
            id=fileobj.id,
            owner_id=fileobj.owner.owner_id,
            owner_type=fileobj.owner.owner_type,
        )
        size = model.Session.scalar(stmt)
        assert not size

        call_action(
            "file_ownership_transfer",
            id=fileobj.id,
            owner_id=fake.unique.uuid4(),
            owner_type=fileobj.owner.owner_type,
        )
        size = model.Session.scalar(stmt)
        assert size == 1

    def test_transfer_unowned(
        self, faker: Faker, file_factory: types.TestFactory[model.File]
    ):
        """Unowned file can be transfered without additional conditions."""
        file = file_factory.model(user="")
        assert not file.owner

        owner_id = fake.unique.uuid4()
        owner_type = faker.word()

        result = call_action(
            "file_ownership_transfer",
            id=file.id,
            owner_id=owner_id,
            owner_type=owner_type,
        )

        assert result["owner_id"] == owner_id
        assert result["owner_type"] == owner_type

    def test_transfer_with_pin(self, faker: Faker, file: dict[str, Any]):
        """File can be pinned during transfer."""

        result = call_action(
            "file_ownership_transfer",
            id=file["id"],
            owner_id=fake.unique.uuid4(),
            owner_type=faker.word(),
        )
        assert not result["pinned"]

        result = call_action(
            "file_ownership_transfer",
            id=file["id"],
            owner_id=fake.unique.uuid4(),
            owner_type=faker.word(),
            pin=True,
        )
        assert result["pinned"]


class TestFileOwnerScan:
    def test_filter_by_owner(
        self, file_factory: types.TestFactory, faker: Faker, user: dict[str, Any]
    ):
        """Files are filtered by owner."""
        owned = file_factory(user=user["name"])
        file_factory(user="")

        result = call_action("file_owner_scan", owner_type="user", owner_id=user["id"])
        assert result["results"] == [owned]

        result = call_action(
            "file_owner_scan", owner_type="user", owner_id=fake.unique.uuid4()
        )
        assert result["results"] == []
