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
from ckan.lib import files
from ckan.tests.factories import fake
from ckan.tests.helpers import call_action
from ckan.logic.action.file import _file_search

call_action: Any


@pytest.mark.usefixtures("non_clean_db")
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


@pytest.mark.usefixtures("non_clean_db")
class TestFileRegister:
    def test_unknown_storage(self, faker: Faker):
        """Unknown storage produces an error."""
        with pytest.raises(tk.ValidationError):
            call_action("file_register", storage=faker.file_name())

    @pytest.mark.ckan_config(
        "ckan.files.storage.test.disabled_capabilities", ["ANALYZE"]
    )
    def test_missing_analyze_capability(self, faker: Faker):
        """Missing ANALYZE capability is reported via validation error."""
        with pytest.raises(tk.ValidationError):
            call_action("file_register", location=faker.file_name())

    def test_already_registered(self, file: dict[str, Any]):
        """If file is registered in the system it causes an error."""
        with pytest.raises(tk.ValidationError):
            call_action("file_register", location=file["location"])

    def test_normal_file(self, faker: Faker):
        """Existing file reported via validation error."""
        storage = files.get_storage()
        info = storage.upload(
            storage.prepare_location(faker.file_name()),
            files.make_upload(faker.binary(100)),
        )

        result = call_action("file_register", location=info.location)
        assert result["location"] == info.location
        assert result["size"] == info.size
        assert result["hash"] == info.hash


@pytest.mark.usefixtures("clean_db")
class TestFileSearch:
    def test_minimal_search(self, file_factory: types.TestFactory):
        """Search without filters returns all files."""
        first, second = file_factory.create_batch(2)
        result = _file_search({}, {})
        assert result["count"] == 2
        assert first in result["results"]
        assert second in result["results"]

    def test_sort(self, file_factory: types.TestFactory, faker: Faker):
        """Results can be sorted by multiple fields with different directions."""
        first = file_factory(name="a.txt", upload=faker.binary(10))
        second = file_factory(name="b.txt", upload=faker.binary(5))

        result = _file_search({}, {"sort": "name"})
        assert [f["id"] for f in result["results"]] == [first["id"], second["id"]]

        result = _file_search({}, {"sort": "size"})
        assert [f["id"] for f in result["results"]] == [second["id"], first["id"]]

        result = _file_search({}, {"sort": [["size", "desc"]]})
        assert [f["id"] for f in result["results"]] == [first["id"], second["id"]]

        result = _file_search({}, {"sort": [["size", "asc"]]})
        assert [f["id"] for f in result["results"]] == [second["id"], first["id"]]

        result = _file_search({}, {"sort": [["owner_id", "desc"], "size"]})
        assert [f["id"] for f in result["results"]] == [second["id"], first["id"]]

        result = _file_search({}, {"sort": [["owner_id", "asc"], "size"]})
        assert [f["id"] for f in result["results"]] == [second["id"], first["id"]]

        result = _file_search({}, {"sort": ["owner_id", ["size", "desc"]]})
        assert [f["id"] for f in result["results"]] == [first["id"], second["id"]]

    def test_filter_by_value(self, faker: Faker, file_factory: types.TestFactory):
        """File can be found by model fields."""
        big = file_factory(upload=faker.binary(100))
        small = file_factory(upload=faker.binary(10))

        result = _file_search({}, {"filters": {}})
        assert result["count"] == 2

        result = _file_search({}, {"filters": {"size": 10}})
        assert result["results"] == [small]

        result = _file_search({}, {"filters": {"size": {"$gte": 50}}})
        assert result["results"] == [big]

        result = _file_search({}, {"filters": {"owner_type": {"$eq": "user"}}})
        assert big in result["results"]
        assert small in result["results"]

        result = _file_search({}, {"filters": {"location": {"$ne": small["name"]}}})

        assert result["results"] == [big]

    def test_filter_by_data(self, faker: Faker, file_factory: types.TestFactory):
        """File can be found by storage/plugin data."""
        big_obj = file_factory.model()
        small_obj = file_factory.model()

        big_obj.storage_data = {"big": True, "size": 100, "name": "big"}
        small_obj.storage_data = {"big": False, "size": 10}
        model.Session.commit()

        big = call_action("file_show", id=big_obj.id)
        small = call_action("file_show", id=small_obj.id)

        result = _file_search({}, {"filters": {"storage_data": {"size": 10}}})
        assert result["results"] == [small]

        result = _file_search({}, {"filters": {"storage_data": {"size": {"$gte": 50}}}})
        assert result["results"] == [big]

        result = _file_search({}, {"filters": {"storage_data": {"big": {"$ne": None}}}})
        assert big in result["results"]
        assert small in result["results"]

        result = _file_search({}, {"filters": {"storage_data": {"big": True}}})
        assert result["results"] == [big]

        result = _file_search({}, {"filters": {"storage_data": {"name": None}}})
        assert result["results"] == [small]

        result = _file_search({}, {"filters": {"storage_data": {"name": "big"}}})
        assert result["results"] == [big]


@pytest.mark.usefixtures("non_clean_db")
class TestFileDelete:
    def test_delete_non_existing(self, faker: Faker):
        """Attempt to remove non-existing file causes an error."""
        with pytest.raises(tk.NotFound):
            call_action("file_delete", id=faker.uuid4())

    @pytest.mark.ckan_config(
        "ckan.files.storage.test.disabled_capabilities", ["REMOVE"]
    )
    def test_missing_remove_capability(
        self,
        file_factory: types.TestFactory,
    ):
        """Missing REMOVE capability is reported via validation error."""
        file = file_factory()
        with pytest.raises(tk.ValidationError):
            call_action("file_delete", id=file["id"])

    def test_delete_real(self, file_factory: types.TestFactory):
        """File can be removed."""
        file = file_factory()
        call_action("file_delete", id=file["id"])
        existing = model.Session.get(model.File, file["id"])
        assert not existing

    def test_delete_missing(self, file_factory: types.TestFactory):
        """File that does not exist in storage but exist in DB can be removed."""
        file = file_factory()
        storage = files.get_storage()
        storage.remove(files.FileData(file["location"]))
        call_action("file_delete", id=file["id"])
        existing = model.Session.get(model.File, file["id"])
        assert not existing


@pytest.mark.usefixtures("non_clean_db")
class TestFileShow:
    def test_show_missing(self, faker: Faker):
        """Attempt to show non-existing file causes an error."""
        with pytest.raises(tk.NotFound):
            call_action("file_show", id=faker.uuid4())

    def test_show_real(self, file: dict[str, Any]):
        """Real file can be shown."""
        result = call_action("file_show", id=file["id"])
        assert result == file


@pytest.mark.usefixtures("non_clean_db")
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


@pytest.mark.usefixtures("non_clean_db")
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


@pytest.mark.usefixtures("non_clean_db")
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


@pytest.mark.usefixtures("non_clean_db")
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

    def test_transfer_expires_owner(
        self, faker: Faker, file_factory: types.TestFactory
    ):
        """Owner attribute of the file is refreshed during transfer."""
        file = file_factory.model(user="")
        assert not file.owner

        call_action(
            "file_ownership_transfer",
            id=file.id,
            owner_id=faker.uuid4(),
            owner_type="user",
        )
        assert file.owner


@pytest.mark.usefixtures("non_clean_db")
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
