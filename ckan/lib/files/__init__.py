from __future__ import annotations

import os
from typing import Any, cast

import file_keeper as fk

import ckan.plugins as p
from ckan.common import config

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
    "storages",
    "adapters",
]


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
        exceptions.UnknownAdapterError: storage adapter is not registered

    Example:
        ```
        storage = make_storage("memo", {"type": "files:redis"})
        ```

    """
    adapter_type = settings.pop("type", None)
    adapter = adapters.get(adapter_type)
    if not adapter:
        raise fk.exc.UnknownAdapterError(adapter_type)

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
        raise fk.exc.UnknownStorageError(name)

    return storage


def collect_adapters() -> dict[str, type[Storage]]:
    result: dict[str, type[Storage]] = {
        "files:fs": default.FsStorage,
    }

    for plugin in p.PluginImplementations(p.IFiles):
        result.update(plugin.files_get_storage_adapters())
    return result


def collect_storages() -> dict[str, Storage]:
    path = config["ckan.storage_path"]
    result = {}

    if path:
        result["resources"] = make_storage(
            "resources",
            {
                "type": "files:fs",
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
                    "type": "files:fs",
                    "path": os.path.join(path, "storage", "uploads", object_type),
                    "create_path": True,
                },
            )

    return result


adapters = fk.Registry["type[Storage]"](collector=collect_adapters)
storages = fk.Registry["Storage"](collector=collect_storages)
