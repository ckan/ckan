from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from faker import Faker

from ckan.exceptions import CkanConfigurationException
import ckan.plugins as p
from ckan.lib import files


class TestMakeStorage:
    def test_name_can_be_either_explicit_or_implicit(self, tmp_path: Path):
        """File-keeper adapters cannot be initialized without CKAN wrapper."""
        storage = files.make_storage("implicit", {"type": "ckan:fs", "path": tmp_path})
        assert storage.settings.name == "implicit"

        storage = files.make_storage(
            "you won't see me",
            {"type": "ckan:fs", "path": tmp_path, "name": "explicit"},
        )
        assert storage.settings.name == "explicit"


class TestGetStorage:
    @pytest.mark.ckan_config("ckan.files.storage.test.type", "invalid")
    def test_default_storage_missing(self):
        """Default storage causes an error if not configured is not configured."""
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
        prefix = (
            "ckan.files.storage." + ckan_config["ckan.files.default_storages.default"]
        )
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


class CustomAdapterPlugin(p.IFiles, p.SingletonPlugin):
    def files_get_storage_adapters(self):
        return {
            "test:custom": files.Storage,
        }


class TestAdapters:
    def test_native_adapters(self):
        """Core and FK adapters are unconditionally available."""
        assert "file_keeper:fs" in files.adapters
        assert "ckan:fs" in files.adapters

    @pytest.mark.with_plugins({"custom_adapter": CustomAdapterPlugin})
    def test_custom_adapters(self):
        """Custom adapters are available only when plugin enabled."""
        assert "test:custom" in files.adapters

        p.unload("custom_adapter")

        assert "test:custom" not in files.adapters


class CustomTransformersPlugin(p.IFiles, p.SingletonPlugin):
    def files_get_location_transformers(self) -> dict[str, files.LocationTransformer]:
        return {"test_upper": lambda location, upload, extras: location.upper()}


class TestLocationTransformers:
    @pytest.mark.with_plugins({"custom_transformers": CustomTransformersPlugin})
    def test_transformers(self, faker: Faker):
        """Location transformers are registered by extensions."""
        storage = files.make_storage(
            "test",
            {"type": "ckan:null", "location_transformers": ["test_upper"]},
        )

        location = faker.file_path()

        assert storage.prepare_location(location) == location.upper()


def test_public_storages_cannot_include_private_storages(
    reset_storages: Any,
    monkeypatch: pytest.MonkeyPatch,
    ckan_config: dict[str, Any],
    tmp_path: Any,
):
    """Test that public storages cannot include private storages in their configuration."""
    tmp_path = str(tmp_path)
    prefix = "ckan.files.storage.test"
    monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
    monkeypatch.setitem(ckan_config, f"{prefix}.path", tmp_path)
    monkeypatch.setitem(ckan_config, f"{prefix}.public", True)

    prefix = "ckan.files.storage.another"
    monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
    monkeypatch.setitem(ckan_config, f"{prefix}.initialize", True)
    monkeypatch.setitem(ckan_config, f"{prefix}.path", tmp_path + "/folder")

    with pytest.raises(CkanConfigurationException):
        reset_storages()

    # storages with different backends do not overlap
    monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:memory")
    reset_storages()
    
    
def test_public_storages_cannot_include_private_storages_startup(
    monkeypatch: pytest.MonkeyPatch,
    ckan_config: dict[str, Any],
    tmp_path: Any,
):
    """Test that if public storages include private storages in their configuration
        CKAN will fail on startup."""
    tmp_path = str(tmp_path)
    prefix = "ckan.files.storage.test"
    monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
    monkeypatch.setitem(ckan_config, f"{prefix}.path", tmp_path)
    monkeypatch.setitem(ckan_config, f"{prefix}.public", True)
    
    prefix = "ckan.files.storage.another"
    monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
    monkeypatch.setitem(ckan_config, f"{prefix}.initialize", True)
    monkeypatch.setitem(ckan_config, f"{prefix}.path", tmp_path + "/folder")

    with pytest.raises(CkanConfigurationException) as e:
        files.collect_storages()


def test_file_system_storage_path_must_be_absolute(
    reset_storages: Any,
    monkeypatch: pytest.MonkeyPatch,
    ckan_config: dict[str, Any],
    tmp_path: Any,
):
   """Test that public storages cannot include private storages in their configuration."""
    prefix = "ckan.files.storage.test"
    monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
    monkeypatch.setitem(ckan_config, f"{prefix}.path", "some_path")
    with pytest.raises(CkanConfigurationException) as e:
        files.collect_storages()

    tmp_path = str(tmp_path)
    prefix = "ckan.files.storage.another"
    monkeypatch.setitem(ckan_config, f"{prefix}.type", "ckan:fs")
    monkeypatch.setitem(ckan_config, f"{prefix}.initialize", True)
    monkeypatch.setitem(ckan_config, f"{prefix}.path", tmp_path + "/folder")    
