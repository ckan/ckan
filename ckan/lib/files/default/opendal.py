from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import opendal as od

from ckan.config.declaration import Declaration, Key
from ckan.lib.files import base


@dataclasses.dataclass()
class Settings(base.Settings, od.Settings):
    pass


class OpenDalStorage(base.Storage, od.OpenDalStorage):
    """Multi-provider cloud storage."""

    settings: Settings
    SettingsFactory = Settings

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.scheme).required().set_description(
            "OpenDAL service type. Check available services at"
            + "  https://docs.rs/opendal/latest/opendal/services/index.html",
        )
        declaration.declare(key.params).set_description(
            "JSON object with parameters passed directly to OpenDAL operator.",
        ).set_validators("default({}) convert_to_json_if_string dict_only")

        declaration.declare(key.path).set_description(
            "Path inside the container where uploaded data will be stored.",
        )
