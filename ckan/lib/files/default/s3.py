from __future__ import annotations

import dataclasses
from typing_extensions import override

from file_keeper.default.adapters import s3

from ckan.config.declaration import Declaration, Key
from ckan.lib.files import base


@dataclasses.dataclass()
class Settings(base.Settings, s3.Settings):
    pass


class S3Storage(base.Storage, s3.S3Storage):
    """AWS S3 adapter."""

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = type("Uploader", (base.Uploader, s3.Uploader), {})
    ReaderFactory = type("Reader", (base.Reader, s3.Reader), {})
    ManagerFactory = type("Manager", (base.Manager, s3.Manager), {})

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.key).set_description("The AWS Access Key.")
        declaration.declare(key.secret).set_description("The AWS Secret Key. ")

        declaration.declare(key.endpoint).set_description("Custom AWS endpoint.")

        declaration.declare(key.bucket).required().set_description(
            "Name of the storage bucket."
        )

        declaration.declare(key.region).set_description("The AWS Region of the bucket.")

        declaration[key.path].set_description(
            "Path inside the bucket where uploaded data will be stored.",
        )
