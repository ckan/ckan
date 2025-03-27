from __future__ import annotations

from collections import defaultdict
import os
from typing import Any, cast

from file_keeper import exc, make_upload, Registry, Location, Upload

import ckan.plugins as p
from ckan.common import config, CKANConfig
from ckan.exceptions import CkanConfigurationException

from . import default
from .base import (
    Storage,
    Reader,
    Manager,
    Uploader,
    FileData,
    MultipartData,
)


__all__ = [
    "get_storage",
    "Storage",
    "Reader",
    "Manager",
    "Uploader",
    "FileData",
    "MultipartData",
    "Upload",
    "Location",
    "storages",
    "adapters",
    "make_upload",
    "exc",
]

STORAGE_PREFIX = "ckan.files.storage."


def make_storage(name: str, settings: dict[str, Any]):
    """Initialize storage instance with specified settings.

    Storage adapter is defined by `type` key of the settings. The rest of
    settings depends on the specific adapter.

    Args:
        name: name of the storage
        settings: configuration for the storage

    Returns:
        storage instance

    Raises:
        UnknownAdapterError: storage adapter is not registered

    Example:
        ```
        storage = make_storage("memo", {"type": "files:redis"})
        ```

    """
    adapter_type = settings.pop("type", None)
    adapter = adapters.get(adapter_type)
    if not adapter:
        raise exc.UnknownAdapterError(adapter_type)

    settings.setdefault("name", name)

    storage = adapter(settings)

    return storage


def get_storage(name: str | None = None) -> Storage:
    """Return existing storage instance.

    Storages are initialized when plugin is loaded. As result, this function
    always returns the same storage object for the given name.

    If no name specified, default storage is returned.

    Args:
        name: name of the configured storage

    Returns:
        storage instance

    Raises:
        UnknownStorageError: storage with the given name is not configured

    Example:
        ```
        default_storage = get_storage()
        storage = get_storage("storage name")
        ```

    """
    if name is None:
        name = cast(str, config["ckan.files.default_storage"])

    storage = storages.get(name)

    if not storage:
        raise exc.UnknownStorageError(name)

    return storage


def collect_adapters() -> dict[str, type[Storage]]:
    result: dict[str, type[Storage]] = {
        "ckan:fs": default.FsStorage,
    }

    for plugin in p.PluginImplementations(p.IFiles):
        result.update(plugin.files_get_storage_adapters())
    return result


def collect_storage_configuration(config: CKANConfig, prefix: str = STORAGE_PREFIX):
    """Return configuration of every storage located in config dictionary."""
    storages = defaultdict(dict)  # type: dict[str, dict[str, Any]]
    prefix_len = len(prefix)

    # first, group config options by the storage name
    for k, v in config.items():
        if not k.startswith(prefix):
            continue

        try:
            name, option = k[prefix_len:].split(".", 1)
        except ValueError:
            continue

        storages[name][option] = v
    return storages


def collect_storages() -> dict[str, Storage]:
    result = {}

    mapping = collect_storage_configuration(config)
    for name, settings in mapping.items():
        try:
            storage = make_storage(name, settings)
        except (
            exc.UnknownAdapterError,
            exc.InvalidStorageConfigurationError,
        ) as err:
            raise CkanConfigurationException(str(err)) from err

        storages.register(name, storage)

    if path := config["ckan.storage_path"]:
        result["resources"] = make_storage(
            "resources",
            {
                "type": "ckan:fs",
                "path": os.path.join(path, "resources"),
                "create_path": True,
                "recursive": True,
                "override_existing": True,
                "location_transformers": ["safe_relative_path"],
            },
        )

        for object_type in ["user", "group", "admin"]:
            name = f"{object_type}_uploads"
            result[name] = make_storage(
                name,
                {
                    "type": "ckan:fs",
                    "path": os.path.join(path, "storage", "uploads", object_type),
                    "create_path": True,
                },
            )

    return result


adapters = Registry["type[Storage]"](collector=collect_adapters)
storages = Registry["Storage"](collector=collect_storages)
