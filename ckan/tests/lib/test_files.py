from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from faker import Faker

import ckan.plugins as p
from ckan.common import CKANConfig
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


class TestCollectStorageConfiguration:
    def test_empty(self):
        """Application does not break without storage configuration."""
        result = files.collect_storage_configuration(CKANConfig())
        assert result == {}

    def test_mixed(self, faker: Faker):
        """Storage configuration is filtered using prefix."""
        prefix = faker.domain_name() + "."
        name = faker.word()

        config = CKANConfig(
            **{
                f"{prefix}{name}.a": 42,
                f"{prefix}{name}.b": None,
                f"{faker.domain_name()}.{name}.other": True,
            }
        )
        assert files.collect_storage_configuration(config) == {}

        result = files.collect_storage_configuration(config, prefix)
        assert result == {name: {"a": 42, "b": None}}

    def test_nested(self, faker: Faker):
        """Storage configuration can be parsed as flat dictionary."""
        name = faker.word()

        config = CKANConfig(
            **{
                f"{name}.nested.a": 1,
                f"{name}.nested.b": 2,
                f"{name}.c": 3,
                f"{name}.other.d": 4,
            }
        )

        nested = files.collect_storage_configuration(config, "")
        assert nested == {name: {"nested": {"a": 1, "b": 2}, "c": 3, "other": {"d": 4}}}

        flat = files.collect_storage_configuration(config, "", flat=True)
        assert flat == {
            name: {
                "nested.a": 1,
                "nested.b": 2,
                "c": 3,
                "other.d": 4,
            }
        }


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
