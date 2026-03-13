from __future__ import annotations


import copy
import logging
import os
from typing import cast, Any

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


def _storages_from_config(
    settings: dict[str, dict[str, Any]],
) -> dict[str, fk.Storage]:
    """Initialize storages from configuration.

    Storages are configured using options with prefix
    ``ckan.files.storage.``. Each storage must have ``type`` option with
    adapter name, and other options depending on adapter type.

    :returns: mapping with storages
    """
    result = {}

    for name, settings in settings.items():
        try:
            storage = make_storage(name, settings)
        except exc.UnknownAdapterError:
            log.warning(
                "Storage '%s' uses unknown adapter '%s' and cannot be initialized.",
                name,
                settings["type"],
            )
            continue
        except exc.InvalidStorageConfigurationError as err:
            raise CkanConfigurationException(str(err)) from err

        result[name] = storage

    return result


def collect_storages() -> dict[str, fk.Storage]:
    """Initialize storages.

    :returns: mapping with storages
    """
    from ckan.config.declaration.load import config_tree

    storage_config = config_tree(config, prefix=STORAGE_PREFIX, depth=-1)
    result = _storages_from_config(storage_config)

    default = config["ckan.files.default_storages.default"]
    if default in result:
        # use default storage to initialize resources storage. It will create
        # `resources` folder inside the default storage and upload files there.
        name = config["ckan.files.default_storages.resource"]
        if name not in result:
            # copy original configuration, not `default.settings`, because the
            # latter may contain cloud connections, credential objects or other
            # derivables from plain configuration.
            settings = copy.deepcopy(storage_config[default])
            settings["name"] = name
            settings["path"] = os.path.join(settings["path"], "resources")
            settings["initialize"] = True
            settings.setdefault("max_size", config["ckan.max_resource_size"] * 1024**2)

            result[name] = make_storage(name, settings)

        # use default storage to initialize storages for public files. These
        # storages will create `storage/uploads/{object_type}` folder inside
        # the default storage and upload files there.
        for object_type in ["user", "group", "admin"]:
            name = config[f"ckan.files.default_storages.{object_type}"]

            if name not in result:
                settings = copy.deepcopy(storage_config[default])
                settings["path"] = os.path.join(
                    settings["path"], "storage", "uploads", object_type
                )
                settings["name"] = name
                settings["initialize"] = True
                settings["public"] = True

                settings.setdefault("max_size", config["ckan.max_image_size"] * 1024**2)

                if object_type in ["user", "group"]:
                    settings.setdefault(
                        "supported_types",
                        config[f"ckan.upload.{object_type}.mimetypes"]
                        + config[f"ckan.upload.{object_type}.types"],
                    )
                storage = make_storage(name, settings)
                result[name] = storage

    if (
        all(
            config[f"ckan.files.default_storages.{object_type}"] in result
            for object_type in ["resource", "user", "group", "admin"]
        )
        and config["ckan.storage_path"]
    ):
        log.warning(
            "All uploads are handled by storages. `ckan.storage_path` has no effect"
        )

    return result


storages = Registry[fk.Storage](collector=collect_storages)
