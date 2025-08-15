from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from typing import Any, ClassVar

import flask
import file_keeper as fk

from typing_extensions import TypeAlias, override
from ckan import types
from ckan.common import config
from ckan.config.declaration import Declaration
from ckan.config.declaration.key import Key

Location: TypeAlias = fk.Location
Capability: TypeAlias = fk.Capability

FileData: TypeAlias = fk.FileData


def is_supported_type(content_type: str, supported: Iterable[str]) -> bool:
    """Check whether content_type matches supported types.

    :param content_type: tested type
    :param supported: collection of supported types
    """
    maintype, subtype = content_type.split("/")
    desired = {content_type, maintype, subtype}
    return any(st in desired for st in supported)


class Uploader(fk.Uploader):
    """Service responsible for writing data into a storage.

    :py:class:`Storage` internally calls methods of this service. For example,
    ``Storage.upload(location, upload, **kwargs)`` results in
    ``Uploader.upload(location, upload, kwargs)``.

    >>> class MyUploader(Uploader):
    >>>     def upload(
    >>>         self, location: Location, upload: Upload, extras: dict[str, Any]
    >>>     ) -> FileData:
    >>>         reader = upload.hashing_reader()
    >>>         with open(location, "wb") as dest:
    >>>             dest.write(reader.read())
    >>>         return FileData(
    >>>             location, upload.size,
    >>>             upload.content_type,
    >>>             reader.get_hash()
    >>>         )

    """


class Reader(fk.Reader):
    """Service responsible for reading data from the storage.

    :py:class:`Storage` internally calls methods of this service. For example,
    ``Storage.stream(data, **kwargs)`` results in ``Reader.stream(data,
    kwargs)``.

    >>> class MyReader(Reader):
    >>>     def stream(
    >>>         self, data: FileData, extras: dict[str, Any]
    >>>     ) -> Iterable[bytes]:
    >>>         return open(data.location, "rb")

    """

    def response(self, data: FileData, extras: dict[str, Any]) -> types.Response:
        if not self.storage.supports(Capability.STREAM):
            raise fk.exc.UnsupportedOperationError("stream", self)

        return flask.Response(
            self.stream(data, extras),
            mimetype=data.content_type or None,
            headers={"Content-length": str(data.size)},
        )


class Manager(fk.Manager):
    """Service responsible for maintenance file operations.

    :py:class:`Storage` internally calls methods of this service. For example,
    ``Storage.remove(data, **kwargs)`` results in ``Manager.remove(data,
    kwargs)``.

    >>> class MyManager(Manager):
    >>>     def remove(
    >>>         self, data: FileData, extras: dict[str, Any]
    >>>     ) -> bool:
    >>>         os.remove(data.location)
    >>>         return True

    """


@dataclasses.dataclass()
class Settings(fk.Settings):
    """Storage settings definition.

    Any configurable parameter must be defined here, as this dataclass accepts options
    collected from CKAN config file and it will raise an exception whenever it sees an
    unknown option.

    Generally, Settings should not validate configuration, because validation is
    provided by the config declarations. Settings object just holds static options and
    initializes additional objects, like connections to external services.

    >>> @dataclasses.dataclass()
    >>> class MySettings(Settings)
    >>>
    >>>     # normal configurable parameter. Prefer this type of settings
    >>>     verbose: bool = False
    >>>
    >>>     # this attribute will be initialized inside __post_init__. All
    >>>     # setting's attributes must be supplied with default values, but we
    >>>     # cannot set "default" connection. Instead we are using `None` and
    >>>     # type-ignore annotation to avoid attention from typechecker. If we
    >>>     # can guarantee that settings will not be initialized without a
    >>>     # connection, that remains safe.
    >>>     conn: Engine = None # pyright: ignore[reportAssignmentType]
    >>>
    >>>     # db_url will be used to initialize connection and
    >>>     # there is no need to keep it after initialization
    >>>     db_url: dataclasses.InitVar[str] = ""
    >>>
    >>>     def __post_init__(self, db_url: str, **kwargs: Any):
    >>>         # always call original implementation
    >>>         super().__post_init__(**kwargs)
    >>>
    >>>         if self.conn is None:  # pyright: ignore[reportUnnecessaryComparison]
    >>>             if not db_url:
    >>>                 msg = "db_url is not valid"
    >>>                 raise files.exc.InvalidStorageConfigurationError(
    >>>                     self.name,
    >>>                     msg,
    >>>                 )
    >>>             self.conn = create_engine(db_url)

    """

    supported_types: list[str] = dataclasses.field(default_factory=list)
    """Supported types of uploads"""
    max_size: int = 0
    """Max allowed size of the upload"""


class Storage(fk.Storage):
    """Base class for storage implementation.

    Extends ``file_keeper.Storage``.

    Implementation of the custom adapter normally includes definition of
    factory classes and config declaration.

    >>> class MyStorage(Storage):
    >>>     # typechecker may need this line to identify types
    >>>     settings: MySettings
    >>>
    >>>     SettingsFactory = MySettings
    >>>     UploaderFactory = MyUploader
    >>>     ManagerFactory = MyManager
    >>>     ReaderFactory = MyReader
    >>>
    >>>     @classmethod
    >>>     def declare_config_options(cls, declaration: Declaration, key: Key):
    >>>         ...

    :param settings: mapping with storage configuration
    """

    settings: Settings
    reader: Reader
    uploader: Uploader
    manager: Manager
    SettingsFactory: ClassVar[type[Settings]] = Settings

    UploaderFactory: ClassVar[type[Uploader]] = Uploader
    ReaderFactory: ClassVar[type[Reader]] = Reader
    ManagerFactory: ClassVar[type[Manager]] = Manager

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        """Declare configuration of the storage.

        All attributes of the storage's SettingsFactory must be defined
        here. In this way user can discover available options using config CLI,
        and configuration is validated/converted by CKAN before it passed to
        the storage.

        >>> @classmethod
        >>> def declare_config_options(cls, decl, key):
        >>>     decl.declare_bool(key.enable_turbo_mode)
        >>>     decl.declare(key.secret).required()
        """
        declaration.declare(key.max_size, 0).append_validators(
            "parse_filesize",
        ).set_description(
            "The maximum size of a single upload."
            + "\nSupports size suffixes: 42B, 2M, 24KiB, 1GB."
            + " `0` means no restrictions.",
        ).set_example("10MB")

        declaration.declare_list(key.supported_types, None).set_description(
            "Space-separated list of full MIME types, or just type/subtype part."
        ).set_example("text/csv pdf application video jpeg")

        declaration.declare_bool(key.override_existing).set_description(
            "If file already exists, replace it with new content."
            + "\nThis option can be ignored by certain adapters.",
        )

        declaration.declare_bool(key.initialize).set_description(
            "Prepare storage backend for uploads(create path, bucket, DB). This op",
        )

        declaration.declare(key.path).set_description(
            "Prefix for the file's location. The actual meaning of this option"
            + " depends on the adapter. FS adapter uses the path as a root folder for uploads."
            + " Cloud adapters, usually, use path as a prefix for the name of uploaded objects.",
        )

        declaration.declare(key.name, key[-1]).set_description(
            "Descriptive name of the storage used for debugging.\nWhen empty,"
            + " name from the config option is used,"
            + " i.e: `ckanext.files.storage.DEFAULT_NAME...`",
        )

        declaration.declare_list(key.location_transformers, None).set_description(
            "List of transformations applied to the file location."
            "\nDepending on the storage type, sanitizing the path or removing"
            " special characters can be sensible.\nEmpty value leaves location"
            " unchanged, `uuid` transforms location into random UUID,"
            "\n`uuid_with_extension` transforms filename into UUID and appends original"
            " file's extension to it.",
        ).set_example("datetime_prefix")

        declaration.declare_list(key.disabled_capabilities, None).set_description(
            "Capabilities that are not supported even if implemented."
            " Can be used to transform fully-featured storage into a read-only/write-only storage."
        )

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

        If rendering is safe and preferable, enable ``send_inline`` flag.

        :param data: file details
        :param filename: expected name of the file used instead of the real name
        :param send_inline: do not force download and try rendering file in browser

        :returns: Flask response with file's content
        """
        resp = self.reader.response(data, kwargs)

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

    def validate_size(self, size: int):
        """Verify that size of upload does not go over the configured limit.

        :param size: the actual size of uploaded file in bytes
        :raises LargeUploadError: upload exceeds allowed size
        """
        max_size = self.settings.max_size
        if max_size and size > max_size:
            raise fk.exc.LargeUploadError(size, max_size)

    def validate_content_type(self, content_type: str):
        """Verify that type of upload is allowed by configuration.

        :param content_type: MIME Type of uploaded file
        :raises WrongUploadTypeError: type of upload is not supported
        """
        supported_types = self.settings.supported_types
        if supported_types and not is_supported_type(
            content_type,
            supported_types,
        ):
            raise fk.exc.WrongUploadTypeError(content_type)

    @override
    def upload(
        self, location: Location, upload: fk.Upload, /, **kwargs: Any
    ) -> FileData:
        """Upload file to the storage.

        Before upload starts, file is validated according to storage
        settings.

        :param location: sanitized location of the file in the storage
        :param upload: uploaded object
        :param \\**kwargs: other parameters that may be used by the storage
        :returns: details of the uploaded file
        """
        self.validate_size(upload.size)
        self.validate_content_type(upload.content_type)

        return super().upload(location, upload, **kwargs)

    @override
    def multipart_start(
        self, location: Location, data: FileData, /, **kwargs: Any
    ) -> FileData:
        """Prepare data for multipart upload.

        Before upload starts, data is validated according to storage settings.

        :param location: sanitized location of the file in the storage
        :param data: details required for upload initialization
        :param \\**kwargs: other parameters that may be used by the storage
        :returns: details of the initiated multipart upload
        """
        self.validate_size(data.size)
        self.validate_content_type(data.content_type)

        return super().multipart_start(data, **kwargs)
