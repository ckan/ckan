from __future__ import annotations

import os
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
