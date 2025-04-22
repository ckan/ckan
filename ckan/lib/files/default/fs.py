from __future__ import annotations

import os
import dataclasses
from typing import Any

import flask
from file_keeper.default.adapters import fs

from ckan import types
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

    def _base_response(
        self, data: base.FileData, extras: dict[str, Any]
    ) -> types.Response:
        filepath = os.path.join(self.settings.path, data.location)
        return flask.send_file(
            filepath,
            download_name=data.location,
            mimetype=data.content_type,
        )
