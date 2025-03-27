from __future__ import annotations

import dataclasses


from time import time
from typing import Any, Iterable

import jwt
import file_keeper as fk

from typing_extensions import TypeAlias


from ckan.config.declaration import Declaration
from ckan.config.declaration.key import Key
from ckan.lib.api_token import _get_algorithm, _get_secret

Uploader: TypeAlias = fk.Uploader
Manager: TypeAlias = fk.Manager
Reader: TypeAlias = fk.Reader

FileData: TypeAlias = fk.FileData
MultipartData: TypeAlias = fk.MultipartData


def is_supported_type(content_type: str, supported: Iterable[str]) -> bool:
    """Check whether content_type matches supported types."""
    maintype, subtype = content_type.split("/")
    desired = {content_type, maintype, subtype}
    return any(st in desired for st in supported)


def encode_token(data: dict[str, Any]) -> str:
    return jwt.encode(data, _get_secret(encode=True), algorithm=_get_algorithm())


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _get_secret(encode=False), algorithms=[_get_algorithm()])


@dataclasses.dataclass()
class Settings(fk.Settings):
    supported_types: list[str] = dataclasses.field(default_factory=list)
    max_size: int = 0


class Storage(fk.Storage):
    """Base class for storage implementation."""

    settings: Settings
    SettingsFactory = Settings

    def validate_size(self, size: int):
        max_size = self.settings.max_size
        if max_size and size > max_size:
            raise fk.exc.LargeUploadError(size, max_size)

    def validate_content_type(self, content_type: str):
        supported_types = self.settings.supported_types
        if supported_types and not is_supported_type(
            content_type,
            supported_types,
        ):
            raise fk.exc.WrongUploadTypeError(content_type)

    def upload(
        self, location: fk.Location, upload: fk.Upload, /, **kwargs: Any
    ) -> FileData:
        self.validate_size(upload.size)
        self.validate_content_type(upload.content_type)

        return super().upload(location, upload, **kwargs)

    def multipart_start(
        self, location: fk.Location, data: MultipartData, /, **kwargs: Any
    ) -> MultipartData:
        self.validate_size(data.size)
        self.validate_content_type(data.content_type)

        return super().multipart_start(location, data, **kwargs)

    def temporal_link(self, data: FileData, /, **kwargs: Any) -> str:
        from ckan.lib.helpers import url_for

        try:
            link = super().temporal_link(data, **kwargs)
        except fk.exc.UnsupportedOperationError:
            link = None

        if not link:
            token = encode_token(
                {
                    "topic": "download_file",
                    "exp": str(int(time()) + kwargs.get("ttl", 30)),
                    "storage": self.settings.name,
                    "location": data.location,
                },
            )
            link = url_for("files.temporal_download", token=token, _external=True)
        return link

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        declaration.declare(key.max_size, 0).append_validators(
            "parse_filesize",
        ).set_description(
            "The maximum size of a single upload."
            + "\nSupports size suffixes: 42B, 2M, 24KiB, 1GB."
            + " `0` means no restrictions.",
        )

        declaration.declare_list(key.supported_types, None).set_description(
            "Space-separated list of MIME types or just type or subtype part."
            + "\nExample: text/csv pdf application video jpeg",
        )

        declaration.declare_bool(key.override_existing).set_description(
            "If file already exists, replace it with new content.",
        )

        declaration.declare(key.name, key[-1]).set_description(
            "Descriptive name of the storage used for debugging. When empty,"
            + " name from the config option is used,"
            + " i.e: `ckanext.files.storage.DEFAULT_NAME...`",
        )

        declaration.declare_list(key.location_transformers, None).set_description(
            "List of transformations applied to the file location."
            " Depending on the storage type, sanitizing the path or removing"
            " special characters can be sensible. Empty value leaves location"
            " unchanged, `uuid` transforms location into UUID, `uuid_with_extension`"
            " transforms filename into UUID and appends original file's extension"
            " to it.",
        )
