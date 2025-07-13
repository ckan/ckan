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
    Storage,
    Settings,
    Uploader,
    Reader,
    Manager,
    Capability,
    FileData,
    MultipartData,
    Location,
)

__all__ = [
    "get_storage",
    "make_upload",
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
    "exc",
]

STORAGE_PREFIX = "ckan.files.storage."

log = logging.getLogger(__name__)


def make_storage(name: str, settings: dict[str, Any]):
    """Initialize storage instance with specified settings.

    Storage adapter is defined by `type` key of the settings. The rest of
    settings depends on the specific adapter.

    >>> storage = make_storage("memo", {"type": "files:redis"})

    :param name: name of the storage
    :param settings: configuration for the storage
    :returns: storage instance
    :raises UnknownAdapterError: storage adapter is not registered
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

    >>> default_storage = get_storage()
    >>> assert default_storage.settings.name == "default"

    >>> try:
    >>>     storage = get_storage("storage name")
    >>> except files.exc.UnknownStorageError:
    >>>     log.exception("Storage 'storage name' is not configured")

    :param name: name of the configured storage
    :returns: storage instance
    :raises UnknownStorageError: storage with the given name is not configured

    """
    if name is None:
        name = cast(str, config["ckan.files.default_storages.default"])

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
        "ckan:public_fs": default.PublicFsStorage,
    }

    if adapter := getattr(default, "LibCloudStorage", None):
        result["ckan:libcloud"] = adapter

    if adapter := getattr(default, "OpenDalStorage", None):
        result["ckan:opendal"] = adapter

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
        name = config["ckan.files.default_storages.resource"]

        if name not in result:
            result[name] = make_storage(
                name,
                {
                    "type": "ckan:fs",
                    "path": os.path.join(path, "resources"),
                    "create_path": True,
                    "recursive": True,
                    "override_existing": True,
                    "location_transformers": ["safe_relative_path"],
                    "max_size": config["ckan.max_resource_size"] * 1024 * 1024,
                },
            )
        else:
            if not result[name].supports(Capability.STREAM | Capability.CREATE):
                msg = f"STREAM and CREATE capabilities are required for storage {name}"
                raise CkanConfigurationException(msg)

        for object_type in ["user", "group", "admin"]:
            name = config[f"ckan.files.default_storages.{object_type}"]

            if name in result:
                if not result[name].supports(Capability.PERMANENT_LINK):
                    msg = f"PERMANENT_LINK capability is required for storage {name}"
                    raise CkanConfigurationException(msg)
                continue

            prefix = os.path.join(os.path.join("uploads", object_type))
            storage = make_storage(
                name,
                {
                    "type": "ckan:public_fs",
                    "path": os.path.join(path, "storage", prefix),
                    "public_prefix": prefix,
                    "create_path": True,
                    "max_size": config["ckan.max_image_size"] * 1024 * 1024,
                },
            )
            result[name] = storage

    return result


adapters = Registry[type[Storage]](collector=collect_adapters)
storages = Registry[Storage](collector=collect_storages)
