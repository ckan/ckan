from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping
from typing import Any, cast

import file_keeper as fk
from file_keeper import Registry, Upload, exc, make_upload, adapters, ext, make_storage
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
    "Settings",
    "Upload",
    "Location",
    "storages",
    "adapters",
    "exc",
]

STORAGE_PREFIX = "ckan.files.storage."

log = logging.getLogger(__name__)


@ext.hookimpl
def register_adapters(registry: Registry[type[Storage]]):
    """Collect adapters from core and IFiles implementations.

    This hook is called by file_keeper inside
    ``file_keeper.ext.register(reset=True)``.

    """
    registry.register("ckan:fs", default.FsStorage)
    registry.register("ckan:public_fs", default.PublicFsStorage)
    registry.register("ckan:null", default.NullStorage)

    if adapter := getattr(default, "LibCloudStorage", None):
        registry.register("ckan:libcloud", adapter)

    if adapter := getattr(default, "OpenDalStorage", None):
        registry.register("ckan:opendal", adapter)

    for plugin in p.PluginImplementations(p.IFiles):
        for k, v in plugin.files_get_storage_adapters().items():
            registry.register(k, v)


@ext.hookimpl
def register_location_transformers(registry: Registry[LocationTransformer]):
    """Collect location transformers from IFiles implementations.

    This hook is called by file_keeper inside
    ``file_keeper.ext.register(reset=True)``.
    """
    for plugin in p.PluginImplementations(p.IFiles):
        for k, v in plugin.files_get_location_transformers().items():
            registry.register(k, v)


def reset():
    """Reset and collect file_keeper extensions.

    This function expects that file_keeper hooks(``file_keeper.ext.hookimpl``)
    will be created in the current module.
    """
    fk_plugin = sys.modules[__name__]
    if not ext.plugin.is_registered(fk_plugin):
        # register CKAN as file_keeper extension on first call
        ext.plugin.register(fk_plugin)

    ext.register(reset=True)


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
                    "initialize": True,
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
                    "initialize": True,
                    "max_size": config["ckan.max_image_size"] * 1024 * 1024,
                },
            )
            result[name] = storage

    return result


storages = Registry[fk.Storage](collector=collect_storages)
