from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from typing import Any

import file_keeper as fk
from typing_extensions import TypeAlias

from ckan.config.declaration import Declaration
from ckan.config.declaration.key import Key

Location: TypeAlias = fk.Location

Uploader: TypeAlias = fk.Uploader
Manager: TypeAlias = fk.Manager
Reader: TypeAlias = fk.Reader

FileData: TypeAlias = fk.FileData
MultipartData: TypeAlias = fk.MultipartData


def is_supported_type(content_type: str, supported: Iterable[str]) -> bool:
    """Check whether content_type matches supported types.

    Args:
        content_type: tested type
        supported: collection of supported types
    """
    maintype, subtype = content_type.split("/")
    desired = {content_type, maintype, subtype}
    return any(st in desired for st in supported)


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Storage settings definition.

    Any configurable parameter must be defined here, as this dataclass accepts
    configuration collected from CKAN config file. Additionally, storage needs
    to define declaration of all configurable parameters to guarantee correct
    types.

    Generally, Settings should not validate configuration. It just holds it and
    initializes additional instances, like connections to external services.
    """

    supported_types: list[str] = dataclasses.field(default_factory=list)
    max_size: int = 0


class Storage(fk.Storage):
    """Base class for storage implementation.

    Implementation of the custom adapter normally includes definition of
    factory classes and config declaration.

    Args:
        settings: mapping with storage configuration

    Example:
        ```py
        class MyStorage(Storage):
            # typechecker may need this line to identify types
            settings: MySettings

            SettingsFactory = MySettings
            UploaderFactory = MyUploader
            ManagerFactory = MyManager
            ReaderFactory = MyReader

            @classmethod
            def declare_config_options(cls, declaration: Declaration, key: Key):
                ...
        ```
    """

    settings: Settings
    SettingsFactory = Settings

    def validate_size(self, size: int):
        """Verify that size of upload does not go over the configured limit.

        Args:
            size: the actual size of uploaded file in bytes

        Raises:
            LargeUploadError: upload exceeds allowed size
        """
        max_size = self.settings.max_size
        if max_size and size > max_size:
            raise fk.exc.LargeUploadError(size, max_size)

    def validate_content_type(self, content_type: str):
        """Verify that type of upload is allowed by configuration.

        Args:
            content_type: MIME Type of uploaded file

        Raises:
            WrongUploadTypeError: type of upload is not supported
        """
        supported_types = self.settings.supported_types
        if supported_types and not is_supported_type(
            content_type,
            supported_types,
        ):
            raise fk.exc.WrongUploadTypeError(content_type)

    def upload(
        self, location: fk.Location, upload: fk.Upload, /, **kwargs: Any
    ) -> FileData:
        """Upload file to the storage.

        Before upload starts, uploaded files is validated according to storage
        settings.

        Args:
            location: sanitized location of the file in the storage
            upload: uploaded object
            **kwargs: other parameters that may be used by the storage

        Returns:
            details of the uploaded file
        """
        self.validate_size(upload.size)
        self.validate_content_type(upload.content_type)

        return super().upload(location, upload, **kwargs)

    def multipart_start(
        self, location: fk.Location, data: MultipartData, /, **kwargs: Any
    ) -> MultipartData:
        """Prepare data for multipart upload.

        Before upload starts, data is validated according to storage settings.

        Args:
            location: sanitized location of the file in the storage
            data: details required for upload initialization
            **kwargs: other parameters that may be used by the storage

        Returns:
            details of the initiated multipart upload
        """
        self.validate_size(data.size)
        self.validate_content_type(data.content_type)

        return super().multipart_start(location, data, **kwargs)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        """Declare configuration of the storage.

        All attributes of the storage's SettingsFactory must be defined
        here. In this way user can discover available options using config CLI,
        and configuration is validated/converted by CKAN before it passed to
        the storage.
        """
        declaration.declare(key.max_size, 0).append_validators(
            "parse_filesize",
        ).set_description(
            "The maximum size of a single upload."
            + "\nSupports size suffixes: 42B, 2M, 24KiB, 1GB."
            + " `0` means no restrictions.",
        ).set_example("10MB")

        declaration.declare_list(key.supported_types, None).set_description(
            "Space-separated list of MIME types, or just type, or subtype part."
        ).set_example("text/csv pdf application video jpeg")

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
        ).set_example("datetime_prefix")
