from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import fs

from ckan.config.declaration import Declaration, Key

from ckan.lib.files import base


@dataclasses.dataclass()
class Settings(base.Settings, fs.Settings):
    pass


class FsStorage(base.Storage, fs.FsStorage):
    """Store files in local filesystem."""

    settings: Settings
    SettingsFactory = Settings

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.path).required().set_description(
            "Path to the folder where uploaded data will be stored.",
        )

        declaration.declare_bool(key.create_path).set_description(
            "Create storage folder if it does not exist.",
        )

        declaration.declare_bool(key.recursive).set_description(
            "Use this flag if files can be stored inside subfolders"
            + " of the main storage path.",
        )
