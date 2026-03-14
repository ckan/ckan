"""In-memory storage adapter for CKAN's file storage system.

This adapter stores files in memory, which is useful for testing and
development purposes. It implements the necessary interfaces defined by CKAN's
file storage system, allowing it to be used as a drop-in replacement for other
storage backends. Note that this adapter is not suitable for production use due
to its limitations in terms of scalability and persistence.

Available only when `testing` config option is enabled.
"""
from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import memory

from ckan.lib.files import base


@dataclasses.dataclass()
class Settings(base.Settings, memory.Settings):
    pass


class MemoryStorage(base.Storage, memory.MemoryStorage):
    """In-memory storage."""

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = type("Uploader", (base.Uploader, memory.Uploader), {})
    ReaderFactory = type("Reader", (base.Reader, memory.Reader), {})
    ManagerFactory = type("Manager", (base.Manager, memory.Manager), {})
