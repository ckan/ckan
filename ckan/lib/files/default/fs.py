from __future__ import annotations

import os
import dataclasses
from typing import Any
from typing_extensions import override

import flask
from file_keeper.default.adapters import fs

from ckan import types
from ckan.config.declaration import Declaration, Key
from ckan.lib.files import base


@dataclasses.dataclass
class Settings(base.Settings, fs.Settings):
    pass


class Reader(base.Reader, fs.Reader):
    @override
    def response(self, data: base.FileData, extras: dict[str, Any]) -> types.Response:
        filepath = os.path.join(self.storage.settings.path, data.location)
        return flask.send_file(
            filepath,
            download_name=data.location,
            mimetype=data.content_type,
        )


class FsStorage(base.Storage, fs.FsStorage):
    """Store files in local filesystem."""

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = type(
        "Uploader", (base.Uploader, fs.Uploader), {}
    )
    ReaderFactory = Reader
    ManagerFactory = type("Manager", (base.Manager, fs.Manager), {})


@dataclasses.dataclass
class PublicSettings(Settings):
    public_prefix: str = ""


class PublicReader(Reader):
    capabilities: base.Capability = (
        fs.Reader.capabilities | base.Capability.PERMANENT_LINK
    )
    storage: PublicFsStorage

    @override
    def permanent_link(self, data: base.FileData, extras: dict[str, Any]) -> str:
        from ckan.lib.helpers import url_for_static

        return url_for_static(
            os.path.join(
                self.storage.settings.public_prefix,
                data.location,
            ),
            _external=True,
        )


class PublicFsStorage(FsStorage):
    """Store files inside a publicly available folder.

    Path of this storage must point to subdirectory of the publicly available
    folder. This folder can be registered as a Flask static folder, or the
    webserver can serve its content directly.

    The storage **does not** register its path as a public directory. The
    storage expects that directory is already somehow exposed to the user and
    relies on this assumption when producing permanent links to the file.

    Example:
        ```pyhon
        # inside plugin's update config
        tk.add_public_directory(config, "/var/shared_folder")

        # storage initialization
        storage = PublicFsStorage({
            # path points to a subfolder of a public directory
            "path": "/var/shared_folder/my/folder",
            # prefix shows what must be added to the filename
            # to produce a correct URL
            "public_prefix": "my/folder",
        })
        ```
    """

    settings: PublicSettings
    SettingsFactory: type[base.Settings] = PublicSettings
    ReaderFactory: type[base.Reader] = PublicReader

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.public_prefix).set_description(
            "URL prefix to use when builing public file's URL.\nFor example,"
            " if storage has path `/var/data/storage/location`,\nand the directory"
            " `/var/data` is registered as Flask static directory,\nthe correct"
            " prefix is `storage/location`"
        )
