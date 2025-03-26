from __future__ import annotations
import os
from ckan.common import config
import file_keeper as fk


def collect_storages() -> dict[str, fk.Storage]:
    path = config["ckan.storage_path"]
    result = {}

    if path:
        for object_type in ["user", "group"]:
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
