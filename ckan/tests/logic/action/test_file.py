from __future__ import annotations

from typing import Any

import pytest

import sqlalchemy as sa
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan import types
from ckan.tests.helpers import call_action

call_action: Any


@pytest.fixture(scope="module", autouse=True)
def cleanup(reset_storages: types.FixtureResetStorages):
    yield
    reset_storages()


class TestFileCreate:
    def test_name_secured(self, file_factory: types.TestFactory):
        """Filename is sanitized even without location transformers."""
        result = file_factory(name="Test file//etc/passwd")
        assert result["name"] == "Test_file_etc_passwd"

    def test_existing(self, file: dict[str, Any], file_factory: types.TestFactory):
        """Existing file reported via validation error."""
        with pytest.raises(tk.ValidationError):
            file_factory(name=file["location"])

    @pytest.mark.ckan_config("ckan.files.storage.test.override_existing", True)
    def test_override_does_not_created_db_duplications(
        self, file: dict[str, Any], file_factory: types.TestFactory
    ):
        """..."""
        file_factory(name=file["location"])
        stmt = model.File.by_location(file["location"], file["storage"])
        num = model.Session.scalar(stmt.with_only_columns(sa.func.count()))
        assert num == 1

    def test_name_deduced_from_file(self):
        """..."""
        ...

    def test_name_explicit(self):
        """..."""
        ...

    def test_storage_explicit(self):
        """..."""
        ...


@pytest.mark.usefixtures("with_plugins", "clean_db", "clean_redis")
class TestFileDelete:
    def test_basic_delete(self, random_file: dict[str, Any]):
        q = model.Session.query(model.File)
        assert q.count() == 1
        call_action("file_delete", id=random_file["id"])
        assert not q.count()


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestFileShow:
    def test_basic_show(self, random_file: dict[str, Any]):
        result = call_action("file_show", id=random_file["id"])
        assert result["id"] == random_file["id"]

        result = call_action("file_show", id=random_file["id"])
        assert result["id"] == random_file["id"]


@pytest.mark.usefixtures("with_plugins", "clean_db", "clean_redis")
class TestTransferOwnership:
    def test_transfer_to_different_entity(
        self,
        random_file: dict[str, Any],
        user: dict[str, Any],
        package: dict[str, Any],
    ):
        call_action(
            "files_transfer_ownership",
            id=random_file["id"],
            owner_type="user",
            owner_id=user["id"],
        )
        file = model.Session.get(model.File, random_file["id"])
        assert file
        assert file.owner
        assert file.owner.owner_id == user["id"]

        call_action(
            "files_transfer_ownership",
            id=random_file["id"],
            owner_type="package",
            owner_id=package["id"],
        )
        file = model.Session.get(model.File, random_file["id"])
        assert file
        assert file.owner
        assert file.owner.owner_id == package["id"]
