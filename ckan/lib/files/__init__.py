from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any, cast

import file_keeper as fk
from file_keeper import Registry, Upload, exc, make_upload
from file_keeper.core.storage import location_transformers
from file_keeper.core.types import LocationTransformer

import ckan.plugins as p
from ckan import types
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


def get_storage(name: str | None = None) -> fk.Storage:
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


def collect_adapters() -> dict[str, type[fk.Storage]]:
    """Collect adapters from core and IFiles implementations.

    :returns: mapping with storage adapters
    """
    result: dict[str, type[fk.Storage]] = {
        name: fk.adapters[name] for name in fk.adapters if not fk.adapters[name].hidden
    }

    result["ckan:fs"] = default.FsStorage
    result["ckan:public_fs"] = default.PublicFsStorage
    result["ckan:null"] = default.NullStorage

    if adapter := getattr(default, "LibCloudStorage", None):
        result["ckan:libcloud"] = adapter

    if adapter := getattr(default, "OpenDalStorage", None):
        result["ckan:opendal"] = adapter

    for plugin in p.PluginImplementations(p.IFiles):
        result.update(plugin.files_get_storage_adapters())

    return result


def collect_storage_configuration(
    config: types.CKANConfig, prefix: str = STORAGE_PREFIX, /, flat: bool = False
) -> Mapping[str, Any]:
    """Return settings of every storage located in the config.

    :param config: mapping with configuration
    :param prefix: common prefix for storage options
    :param flat: do not transfrom nested keys into dictionaries

    :returns: dictionary with configuration of all storages

    """
    return config.subtree(prefix, depth=1 if flat else -1)


def collect_storages() -> dict[str, fk.Storage]:
    """Initialize configured storages.

    :returns: mapping with storages
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


def collect_location_transformers() -> dict[str, LocationTransformer]:
    """Collect transformers IFiles implementations.

    :returns: mapping with location transformers
    """
    result: dict[str, LocationTransformer] = {}

    for plugin in p.PluginImplementations(p.IFiles):
        result.update(plugin.files_get_location_transformers())

    for name, func in result.items():
        location_transformers.register(name, func)

    return result


adapters = Registry[type[fk.Storage]](collector=collect_adapters)
storages = Registry[fk.Storage](collector=collect_storages)
