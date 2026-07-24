"""Null storage adapter for CKAN.

This adapter does not actually store files, making it useful for testing and
development purposes where file persistence is not required. It implements the
necessary interfaces defined by CKAN's file storage system, allowing it to be
used as a drop-in replacement for other storage backends. Note that this
adapter is not suitable for production use.

Available only when `testing` config option is enabled.
"""
from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import null

from ckan.lib.files import base


@dataclasses.dataclass()
class Settings(base.Settings, null.Settings):
    pass


class NullStorage(base.Storage, null.NullStorage):
    """No-op storage."""

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = type(
        "Uploader", (base.Uploader, null.Uploader), {}
    )
    ReaderFactory = type("Reader", (base.Reader, null.Reader), {})
    ManagerFactory = type(
        "Manager", (base.Manager, null.Manager), {}
    )
