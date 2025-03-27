from __future__ import annotations

import os
from typing import Any, cast

import file_keeper as fk

import ckan.plugins as p
from ckan.common import config

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
    storage = fk.make_storage(name, settings)
    if not isinstance(storage, Storage):
        msg = "Does not extend ckan.lib.files.Storage"
        raise fk.exc.InvalidStorageConfigurationError(name, msg)
    return storage


def get_storage(name: str | None = None) -> fk.Storage:
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
    result = {}
    # result = {
    #     "files:fs": storage.FsStorage,
    #     "files:public_fs": storage.PublicFsStorage,
    #     "files:ckan_resource_fs": storage.CkanResourceFsStorage,
    #     "files:redis": storage.RedisStorage,
    #     "files:filebin": storage.FilebinStorage,
    #     "files:db": storage.DbStorage,
    #     "files:link": storage.LinkStorage,
    # }
    #     adapters: dict[str, type[base.Storage]] = {
    #     }

    #     if hasattr(storage, "S3Storage"):
    #         adapters.update({"files:s3": storage.S3Storage})

    #     if hasattr(storage, "GoogleCloudStorage"):
    #         adapters.update({"files:google_cloud_storage": storage.GoogleCloudStorage})

    #     if hasattr(storage, "OpenDalStorage"):
    #         adapters.update({"files:opendal": storage.OpenDalStorage})

    #     if hasattr(storage, "LibCloudStorage"):
    #         adapters.update({"files:libcloud": storage.LibCloudStorage})

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
                "type": "file_keeper:fs",
                "path": os.path.join(path, "resources"),
                "create_path": True,
                "recursive": True,
                "override_existing": True,
                "location_transformers": ["safe_relative_path"],
            },
        )

        for object_type in ["user", "group", "admin"]:
            name = f"{object_type}_uploads"
            result[name] = fk.make_storage(
                name,
                {
                    "type": "file_keeper:fs",
                    "path": os.path.join(path, "storage", "uploads", object_type),
                    "create_path": True,
                },
            )

    return result


adapters = fk.Registry["type[Storage]"](collector=collect_adapters)
storages = fk.Registry["Storage"](collector=collect_storages)
