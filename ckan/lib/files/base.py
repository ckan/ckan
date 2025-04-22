from __future__ import annotations

from urllib.parse import quote
import dataclasses
from collections.abc import Iterable
from typing import Any

import flask
import file_keeper as fk

from typing_extensions import TypeAlias
from ckan import types
from ckan.common import config
from ckan.config.declaration import Declaration
from ckan.config.declaration.key import Key

Location: TypeAlias = fk.Location
Capability: TypeAlias = fk.Capability

Uploader: TypeAlias = fk.Uploader
Manager: TypeAlias = fk.Manager

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

    Example:
        ```py
        @dataclasses.dataclass()
        class MySettings(Settings)

            # normal configurable parameter. Prefer this type of settings
            verbose: bool = False

            # this attribute will be initialized inside __post_init__. All
            # setting's attributes must be supplied with default values, but we
            # cannot set "default" connection. Instead we are using `None` and
            # type-ignore annotation to avoid attention from typechecker. If we
            # can guarantee that settings will not be initialized without a
            # connection, that's ok.
            conn: Engine = None # type: ignore

            # db_url will be used to initialize connection and
            # there is no need to keep it after that
            db_url: dataclasses.InitVar[str] = ""

            def __post_init__(self, db_url: str, **kwargs: Any):
                # always call original implementation
                super().__post_init__(**kwargs)

                if not db_url:
                    msg = "db_url is not valid"
                    raise files.exc.InvalidStorageConfigurationError(
                        self.name,
                        msg,
                    )
                self.conn = create_engine(db_url)
        ```
    """

    supported_types: list[str] = dataclasses.field(default_factory=list)
    max_size: int = 0


class Reader(fk.Reader):
    """Service responsible for reading data from the storage.

    `Storage` internally calls methods of this service. For example,
    `Storage.stream(data, **kwargs)` results in `Reader.stream(data, kwargs)`.

    Example:
        ```python
        class MyReader(Reader):
            def stream(
                self, data: FileData, extras: dict[str, Any]
            ) -> Iterable[bytes]:
                return open(data.location, "rb")
        ```
    """

    def as_response(self, data: FileData, extras: dict[str, Any]) -> types.Response:
        if not self.capabilities.can(Capability.STREAM):
            raise fk.exc.UnsupportedOperationError("stream", self.storage)

        return flask.Response(self.stream(data, extras), mimetype=data.content_type)


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
    reader: Reader
    SettingsFactory = Settings
    ReaderFactory = Reader

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
        self, location: Location, upload: fk.Upload, /, **kwargs: Any
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
        self, location: Location, data: MultipartData, /, **kwargs: Any
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

    def as_response(
        self,
        data: FileData,
        filename: str | None = None,
        /,
        send_inline: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Make Flask response with file attachment.

        By default, files are served as attachments and are downloaded as
        result.

        If rendering is safe and preferable enable ``send_inline`` flag.

        Args:
            data: file details
            filename: expected name of the file used instead of the real name

        Keyword args:
            send_inline: do not force download and try rendering file in browser

        Returns:
            Flask response with file's content
        """
        resp = self.reader.as_response(data, kwargs)

        inline_types = config["ckan.files.inline_content_types"]
        disposition = (
            "inline"
            if send_inline or is_supported_type(data.content_type, inline_types)
            else "attachment"
        )

        resp.headers.set(
            "content-disposition",
            disposition,
            filename=filename or data.location,
        )

        return resp
