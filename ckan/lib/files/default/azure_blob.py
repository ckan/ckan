from __future__ import annotations

import dataclasses
from typing_extensions import override

from file_keeper.default.adapters import azure_blob

from ckan.config.declaration import Declaration, Key
from ckan.lib.files import base


@dataclasses.dataclass()
class Settings(base.Settings, azure_blob.Settings):
    pass


class AzureBlobStorage(base.Storage, azure_blob.AzureBlobStorage):
    """Azure Blob Storage adapter."""

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = type("Uploader", (base.Uploader, azure_blob.Uploader), {})
    ReaderFactory = type("Reader", (base.Reader, azure_blob.Reader), {})
    ManagerFactory = type("Manager", (base.Manager, azure_blob.Manager), {})

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.account_name).required().set_description(
            "Name of the Azure account."
        )
        declaration.declare(key.account_key).required().set_description(
            "Key for the Azure account."
        )

        declaration.declare(
            key.account_url, "https://{account_name}.blob.core.windows.net"
        ).set_description("Custom resource URL.")

        declaration.declare(key.container_name).required().set_description(
            "Name of the storage container."
        )

        declaration[key.path].set_description(
            "Path inside the container where uploaded data will be stored.",
        )
