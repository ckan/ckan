from __future__ import annotations

import logging
import os
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, cast

from file_keeper import Registry, Upload, exc, make_upload

import ckan.plugins as p
from ckan.common import config
from ckan.exceptions import CkanConfigurationException

from . import default
from .base import (
    Capability,
    FileData,
    Location,
    Manager,
    MultipartData,
    Reader,
    Settings,
    Storage,
    Uploader,
)

__all__ = [
    "get_storage",
    "Capability",
    "Storage",
    "Reader",
    "Manager",
    "Uploader",
    "FileData",
    "MultipartData",
    "Settings",
    "Upload",
    "Location",
    "storages",
    "adapters",
    "make_upload",
    "exc",
]

STORAGE_PREFIX = "ckan.files.storage."

log = logging.getLogger(__name__)


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
        ```py
        storage = make_storage("memo", {"type": "files:redis"})
        ```

    """
    adapter_type = settings.pop("type", None)
    adapter = adapters.get(adapter_type)
    if not adapter:
        raise exc.UnknownAdapterError(adapter_type)

    settings.setdefault("name", name)

    return adapter(settings)


def get_storage(name: str | None = None) -> Storage:
    """Return existing storage instance.

    If no name specified, default storage is returned.

    Storages are initialized when application is loaded. As result, this
    function always returns the same storage object for the given name. But if
    configuration changes in runtime, storage registry must be updated
    manually.

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
    """Collect adapters from core and IFiles implementations.

    Returns:
        mapping with storage adapters
    """
    result: dict[str, type[Storage]] = {
        "ckan:fs": default.FsStorage,
        "ckan:libcloud": default.LibCloudStorage,
    }

    for plugin in p.PluginImplementations(p.IFiles):
        result.update(plugin.files_get_storage_adapters())

    return result


def collect_storage_configuration(
    config: Mapping[str, Any], prefix: str = STORAGE_PREFIX, /, flat: bool = False
):
    """Return settings of every storage located in the config.

    Args:
        config: mapping with configuration
        prefix: common prefix for storage options

    Keyword Args:
        flat: do not transfrom nested keys into dictionaries

    Returns:
        dictionary with configuration of all storages

    """
    storages = defaultdict(dict)  # type: dict[str, dict[str, Any]]
    prefix_len = len(prefix)

    # first, group config options by the storage name
    for k, v in config.items():
        if not k.startswith(prefix):
            continue

        # when `flat` flag is enabled, nested keys `a.b.c` kept as a string:
        # `{"a.b.c": ...}`. When it's disabled, transform such keys into nested
        # dictionaries `{"a": {"b": {"c": ...}}}`
        name, *path = k[prefix_len:].split(".", 1 if flat else -1)
        if not path:
            log.warning("Unrecognized storage configuration: %s = %s", k, v)
            continue

        here = storages[name]
        for segment in path[:-1]:
            here = here.setdefault(segment, {})

        here[path[-1]] = v

    return storages


def collect_storages() -> dict[str, Storage]:
    """Initialize configured storages.

    Returns:
        mapping with storages
    """
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

        result[name] = storage


    if path := config["ckan.storage_path"]:
        if "resources" not in result:
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
            if name in result:
                continue

            result[name] = make_storage(
                name,
                {
                    "type": "ckan:fs",
                    "path": os.path.join(path, "storage", "uploads", object_type),
                    "create_path": True,
                },
            )

    return result


adapters = Registry[type[Storage]](collector=collect_adapters)
storages = Registry[Storage](collector=collect_storages)
