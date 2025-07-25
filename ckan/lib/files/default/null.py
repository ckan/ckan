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
