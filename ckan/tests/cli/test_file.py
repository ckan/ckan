from __future__ import annotations

import pytest

from faker import Faker
from typing import Any
from ckan import types
from ckan.lib import files

from ckan.cli.cli import ckan
from ckan.tests.helpers import CKANCliRunner, call_action


@pytest.fixture
def with_temporal_storage(
    reset_storages: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmpdir: Any,
    ckan_config: dict[str, Any],
):
    monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
    reset_storages()


class TestFilesAdapters(object):
    def test_adapters_list(self, cli: CKANCliRunner):
        """At least adapters name are shown."""
        result = cli.invoke(ckan, ["file", "adapters"])

        assert "ckan:fs" in result.output
        assert "ckan:fs:public" in result.output

    def test_individual_adapter(self, cli: CKANCliRunner):
        """Can show information for a single adapter."""
        result = cli.invoke(ckan, ["file", "adapters", "ckan:fs"])
        assert "ckan:fs" in result.output
        assert "ckan:fs:public" not in result.output

    def test_non_compatible(self, cli: CKANCliRunner):
        """Can show information about external adapters."""
        result = cli.invoke(ckan, ["file", "adapters", "-a"])
        assert "ckan:fs" in result.output
        assert "file_keeper:fs" in result.output

    def test_adapters_with_doc(self, cli: CKANCliRunner):
        """Adapters can be listed with documentation."""
        result = cli.invoke(ckan, ["file", "adapters", "-d"])

        assert "Store files in local filesystem" in result.output

    def test_adapters_with_conf(self, cli: CKANCliRunner):
        """Adapters be listed with configuration."""
        result = cli.invoke(ckan, ["file", "adapters", "-c"])
        assert "ckan.files.storage.NAME.initialize" in result.output


@pytest.mark.usefixtures("with_temporal_storage")
class TestStorageScan:
    def test_resources_scan(
        self,
        cli: CKANCliRunner,
        faker: Faker,
    ):
        """Storage can be scanned."""
        first = faker.file_name()
        second = faker.file_name()

        storage = files.get_storage("resources")
        storage.upload(storage.prepare_location(first), files.make_upload(b""))
        storage.upload(storage.prepare_location(second), files.make_upload(b""))

        result = cli.invoke(ckan, ["file", "storage", "scan", "-s", "resources"])
        assert first in result.output
        assert second in result.output

    @pytest.mark.usefixtures("non_clean_db")
    def test_known_and_unknown(
        self,
        cli: CKANCliRunner,
        faker: Faker,
        file_factory: types.TestFactory,
    ):
        """Known and unknown files can be identified."""
        known = file_factory(storage="resources", upload=faker.binary(10))["name"]

        unknown = faker.file_name()
        storage = files.get_storage("resources")
        storage.upload(files.Location(unknown), files.make_upload(faker.binary(42)))

        result = cli.invoke(
            ckan,
            [
                "file",
                "storage",
                "scan",
                "-s",
                "resources",
                "--known-mark=+",
                "--unknown-mark=-",
            ],
        )
        assert f"+ {known}" in result.output
        assert f"- {unknown}" in result.output

        result = cli.invoke(
            ckan,
            [
                "file",
                "storage",
                "scan",
                "-s",
                "resources",
                "-v",
            ],
        )
        assert "Size: 10B" in result.output
        assert "Size: 42B" not in result.output

        result = cli.invoke(
            ckan,
            [
                "file",
                "storage",
                "scan",
                "-s",
                "resources",
                "-vv",
            ],
        )
        assert "Size: 10B" in result.output
        assert "Size: 42B" in result.output


class TestStorageTransfer:
    def test_copy_between_storages(
        self,
        cli: CKANCliRunner,
        faker: Faker,
    ):
        """Files can be copied between storages."""
        name = faker.file_name()

        group = files.get_storage("group_uploads")
        user = files.get_storage("user_uploads")

        info = group.upload(group.prepare_location(name), files.make_upload(b""))

        assert group.exists(info)
        assert not user.exists(info)

        cli.invoke(
            ckan, ["file", "storage", "transfer", "group_uploads", "user_uploads"]
        )

        assert group.exists(info)
        assert user.exists(info)

    def test_move_between_storages(
        self,
        cli: CKANCliRunner,
        faker: Faker,
    ):
        """Files can be moved between storages."""
        name = faker.file_name()

        group = files.get_storage("group_uploads")
        user = files.get_storage("user_uploads")

        info = group.upload(group.prepare_location(name), files.make_upload(b""))

        assert group.exists(info)
        assert not user.exists(info)

        cli.invoke(
            ckan,
            ["file", "storage", "transfer", "group_uploads", "user_uploads", "-r"],
        )

        assert not group.exists(info)
        assert user.exists(info)

    def test_move_registered_file(
        self,
        cli: CKANCliRunner,
        file_factory: types.TestFactory,
        faker: Faker,
    ):
        """Storage details updated for registered files."""
        group = files.get_storage("group_uploads")
        user = files.get_storage("user_uploads")

        result = file_factory(storage="group_uploads")
        info = files.FileData.from_dict(result)

        # file moved using location
        cli.invoke(
            ckan,
            [
                "file",
                "storage",
                "transfer",
                "group_uploads",
                "user_uploads",
                "-r",
                "-l",
                result["location"],
            ],
        )

        assert not group.exists(info)
        assert user.exists(info)
        moved_result = call_action("file_show", id=result["id"])
        assert moved_result["storage"] == "user_uploads"

        # file moved back using ID
        cli.invoke(
            ckan,
            [
                "file",
                "storage",
                "transfer",
                "user_uploads",
                "group_uploads",
                "-r",
                "-i",
                result["id"],
            ],
        )

        assert group.exists(info)
        assert not user.exists(info)
        moved_result = call_action("file_show", id=result["id"])
        assert moved_result["storage"] == "group_uploads"
