from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import gcs
from typing_extensions import override

from ckan.config.declaration import Declaration, Key
from ckan.lib.files import base


@dataclasses.dataclass()
class Settings(base.Settings, gcs.Settings):
    pass


class GoogleCloudStorage(base.Storage, gcs.GoogleCloudStorage):
    """Google Cloud Storage adapter."""

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = type("Uploader", (base.Uploader, gcs.Uploader), {})
    ReaderFactory = type("Reader", (base.Reader, gcs.Reader), {})
    ManagerFactory = type("Manager", (base.Manager, gcs.Manager), {})

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.bucket_name).required().set_description(
            "Name of the storage bucket."
        )
        declaration.declare(key.credentials_file, "").set_description(
            "Path to the JSON with cloud credentials."
        )

        declaration.declare(key.project_id, "").set_description(
            "The project which the client acts on behalf of."
        )

        declaration.declare(key.client_options).set_description(
            "Additional options for the client connection."
        ).set_validators("ignore_missing convert_to_json_if_string dict_only")

        declaration[key.path].set_description(
            "Path inside the bucket where uploaded data will be stored.",
        )
