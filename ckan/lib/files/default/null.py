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
    SettingsFactory: type[base.Settings] = Settings
    UploaderFactory: type[base.Uploader] = type(
        "Uploader", (base.Uploader, null.Uploader), {}
    )
    ReaderFactory: type[base.Reader] = type("Reader", (base.Reader, null.Reader), {})
    ManagerFactory: type[base.Manager] = type(
        "Manager", (base.Manager, null.Manager), {}
    )
