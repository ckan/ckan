from __future__ import annotations

import dataclasses
from typing_extensions import override

from file_keeper.default.adapters import libcloud as lc

from ckan.config.declaration import Declaration, Key
from ckan.lib.files import base


PROVIDERS_URL = (
    "https://libcloud.readthedocs.io/en/stable/storage/"
    + "supported_providers.html#provider-matrix"
)


@dataclasses.dataclass()
class Settings(base.Settings, lc.Settings):
    pass


class LibCloudStorage(base.Storage, lc.LibCloudStorage):
    """Multi-provider cloud storage."""

    settings: Settings
    SettingsFactory = Settings
    UploaderFactory = type(
        "Uploader", (base.Uploader, lc.Uploader), {}
    )
    ReaderFactory = type("Reader", (base.Reader, lc.Reader), {})
    ManagerFactory = type("Manager", (base.Manager, lc.Manager), {})

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.provider).required().set_description(
            "apache-libcloud storage provider. List of providers available at\n"
            + PROVIDERS_URL
            + ".\nUse upper-cased value from Provider Constant column",
        )
        declaration.declare(key.key).required().set_description(
            "API key or username",
        )
        declaration.declare(key.secret).set_description("Secret password")
        declaration.declare(key.container_name).required().set_description(
            "Name of the container(bucket)",
        )
        declaration.declare(key.params).set_description(
            "JSON object with additional parameters passed directly"
            + " to storage constructor.",
        ).set_validators("default({}) convert_to_json_if_string dict_only")

        declaration.declare(key.path, "").set_description(
            "Path inside the container where uploaded data will be stored.",
        )

        declaration.declare(key.public_prefix).set_description(
            "URL prefix to use when builing public file's URL.\nUsually, this "
            "requires a container with public URL.\nFor example, if storage "
            "uses cloud provider `example.cloud.com`\nand files are uploaded "
            "into container `my_files`, the public prefix must be set to\n"
            "`https://certain.cloud.com/my_files`, assuming container can be "
            "anonymously accessed via this URL.\nFile location will be appended"
            " to public prefix, producing absolute public URL."
        )
