from __future__ import annotations

import logging
import os
from typing import cast

import file_keeper as fk
from file_keeper import Registry, Upload, adapters, exc, ext, make_storage, make_upload
from file_keeper.core.utils import ensure_setup

from ckan.common import config
from ckan.exceptions import CkanConfigurationException

from .base import (
    Capability,
    FileData,
    Location,
    Manager,
    Reader,
    Settings,
    Storage,
    Uploader,
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


def collect_storages() -> dict[str, fk.Storage]:
    """Initialize configured storages.

    :returns: mapping with storages
    """
    from ckan.config.declaration.load import config_tree

    result = {}

    mapping = config_tree(config, prefix=STORAGE_PREFIX, depth=-1)

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
