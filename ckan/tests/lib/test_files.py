from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ckan.lib import files


class TestMakeStorage:
    def test_only_ckan_adapters_are_available(self, tmp_path: Path):
        """File-keeper adapters cannot be initialized without CKAN wrapper."""
        with pytest.raises(files.exc.UnknownAdapterError):
            files.make_storage("test", {"type": "file_keeper:fs", "path": tmp_path})

        assert files.make_storage("test", {"type": "ckan:fs", "path": tmp_path})


class TestGetStorage:
    def test_default_storage_missing(self, reset_storages: Any):
        """Default storage is not configured by default."""
        reset_storages()
        with pytest.raises(files.exc.UnknownStorageError):
            files.get_storage()

    def test_default_storage_present(
        self,
        reset_storages: Any,
        monkeypatch: pytest.MonkeyPatch,
        ckan_config: dict[str, Any],
        tmp_path: Path,
    ):
        """Default storage can be configured and initialized."""
        prefix = "ckan.files.storage.default"
        monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
        monkeypatch.setitem(ckan_config, f"{prefix}.path", tmp_path)

        reset_storages()
        assert files.get_storage()

    def test_custom_storage(
        self,
        reset_storages: Any,
        monkeypatch: pytest.MonkeyPatch,
        ckan_config: dict[str, Any],
        tmp_path: Path,
    ):
        """Arbitrary storage can be configured and initialized."""
        prefix = "ckan.files.storage.test"
        monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
        monkeypatch.setitem(ckan_config, f"{prefix}.path", tmp_path)

        prefix = "ckan.files.storage.another"
        monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
        monkeypatch.setitem(ckan_config, f"{prefix}.path", tmp_path)

        reset_storages()
        assert files.get_storage("test")
        assert files.get_storage("another")
