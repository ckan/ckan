from __future__ import annotations

from _pytest.monkeypatch import MonkeyPatch
from faker import Faker
from ckan.lib import files

from ckan.cli.cli import ckan
from ckan.tests.factories import Any
from ckan.tests.helpers import CKANCliRunner


class TestFilesAdapters(object):
    def test_adapters_list(self, cli: CKANCliRunner):
        """At least adapters name are shown."""
        result = cli.invoke(ckan, ["files", "adapters"])

        assert "ckan:fs" in result.output
        assert "ckan:public_fs" in result.output

    def test_individual_adapter(self, cli: CKANCliRunner):
        """Can show information for a single adapter."""
        result = cli.invoke(ckan, ["files", "adapters", "ckan:public_fs"])
        assert "ckan:fs" not in result.output
        assert "ckan:public_fs" in result.output

    def test_non_compatible(self, cli: CKANCliRunner):
        """Can show information about external adapters."""
        result = cli.invoke(ckan, ["files", "adapters", "-a"])
        assert "ckan:fs" in result.output
        assert "file_keeper:fs" in result.output

    def test_adapters_with_doc(self, cli: CKANCliRunner):
        """Adapters can be listed with documentation."""
        result = cli.invoke(ckan, ["files", "adapters", "-d"])

        assert "Store files in local filesystem" in result.output

    def test_adapters_with_conf(self, cli: CKANCliRunner):
        """Adapters be listed with configuration."""
        result = cli.invoke(ckan, ["files", "adapters", "-c"])
        assert "ckan.files.storage.NAME.create_path" in result.output


class TestStorageScan:
    def test_resources_scan(
        self,
        cli: CKANCliRunner,
        reset_storages: Any,
        monkeypatch: MonkeyPatch,
        tmpdir: Any,
        ckan_config: dict[str, Any],
        faker: Faker,
    ):
        """Storage can be scanned."""
        monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
        reset_storages()

        first = faker.file_name()
        second = faker.file_name()

        storage = files.get_storage("resources")
        storage.upload(storage.prepare_location(first), files.make_upload(b""))
        storage.upload(storage.prepare_location(second), files.make_upload(b""))

        result = cli.invoke(ckan, ["files", "storage", "scan", "-s", "resources"])
        assert first in result.output
        assert second in result.output


class TestStorageTransfer:
    def test_copy_between_storages(
        self,
        cli: CKANCliRunner,
        reset_storages: Any,
        monkeypatch: MonkeyPatch,
        tmpdir: Any,
        ckan_config: dict[str, Any],
        faker: Faker,
    ):
        """Files can be copied between storages."""
        monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
        reset_storages()
        name = faker.file_name()

        group = files.get_storage("group_uploads")
        user = files.get_storage("user_uploads")

        info = group.upload(group.prepare_location(name), files.make_upload(b""))

        assert group.exists(info)
        assert not user.exists(info)

        cli.invoke(
            ckan, ["files", "storage", "transfer", "group_uploads", "user_uploads"]
        )

        assert group.exists(info)
        assert user.exists(info)

    def test_move_between_storages(
        self,
        cli: CKANCliRunner,
        reset_storages: Any,
        monkeypatch: MonkeyPatch,
        tmpdir: Any,
        ckan_config: dict[str, Any],
        faker: Faker,
    ):
        """Files can be moved between storages."""
        monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
        reset_storages()

        name = faker.file_name()

        group = files.get_storage("group_uploads")
        user = files.get_storage("user_uploads")

        info = group.upload(group.prepare_location(name), files.make_upload(b""))

        assert group.exists(info)
        assert not user.exists(info)

        cli.invoke(
            ckan,
            ["files", "storage", "transfer", "group_uploads", "user_uploads", "-r"],
        )

        assert not group.exists(info)
        assert user.exists(info)
