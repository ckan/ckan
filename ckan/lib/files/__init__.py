from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any, cast

import file_keeper as fk
from file_keeper import Registry, Upload, exc, make_upload, adapters, ext, make_storage

from file_keeper.core.utils import ensure_setup


from ckan import types
from ckan.common import config
from ckan.exceptions import CkanConfigurationException

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


@ensure_setup
def reset():
    """Reset and collect file_keeper extensions.

    Because CKAN extends file-keeper as well, this call collects all adapters
    and location transformers registered throught IFiles interface.
    """
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
                if not result[name].supports(Capability.LINK_PERMANENT):
                    msg = f"LINK_PERMANENT capability is required for storage {name}"
                    raise CkanConfigurationException(msg)
                continue

            prefix = os.path.join(os.path.join("uploads", object_type))
            storage = make_storage(
                name,
                {
                    "type": "ckan:fs:public",
                    "path": os.path.join(path, "storage", prefix),
                    "public_prefix": prefix,
                    "initialize": True,
                    "max_size": config["ckan.max_image_size"] * 1024 * 1024,
                },
            )
            result[name] = storage

    return result


# def get_owner(owner_type: str, owner_id: str):
#     """Return owner object by type and ID."""
#     from ckan import model

#     if getter := owner_getters.get(owner_type):
#         return getter(owner_id)

#     owner_model = "group" if owner_type == "organization" else owner_type
#     mappers = model.registry.mappers

#     for mapper in mappers:
#         cls = mapper.class_
#         table = getattr(cls, "__table__", None)
#         if table is None:
#             table = getattr(mapper, "local_table", None)

#         if table is not None and table.name == owner_model:
#             return model.Session.get(cls, owner_id)

#     log.warning("Unknown owner type %s with ID %s", owner_type, owner_id)


storages = Registry[fk.Storage](collector=collect_storages)
# owner_getters = Registry[Callable[[str], Any]]({})
