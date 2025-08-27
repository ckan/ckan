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
