from __future__ import annotations

import os
from typing import cast
import file_keeper as fk

from ckan.common import config


def collect_storages() -> dict[str, fk.Storage]:
    path = config["ckan.storage_path"]
    result = {}

    if path:
        result["resources"] = fk.make_storage(
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


storages = fk.Registry[fk.Storage](collector=collect_storages)


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
