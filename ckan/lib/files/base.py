from __future__ import annotations

import dataclasses
import logging
from typing import Any, ClassVar

import file_keeper as fk
import flask
from typing_extensions import TypeAlias, override

from ckan import types
from ckan.common import config
from ckan.config.declaration import Declaration
from ckan.config.declaration.key import Key

Location: TypeAlias = fk.Location
Capability: TypeAlias = fk.Capability

FileData: TypeAlias = fk.FileData

log = logging.getLogger(__name__)


def is_supported_type(content_type: str | None, supported: list[str]) -> bool:
    """Check whether content_type matches supported types.

    Content type and list of supported types must be specified in
    ``type/subtype`` format.

    Additionally, supported type can be specified as a single ``*``, which
    accepts any format. When using ``*``, do not add any other supported types,
    as ``*`` will accept any value and there is no sense in additional options.

    If either ``content_type`` or ``supported`` is empty, function returns
    ``True``.

    >>> is_supported_type("video/mp4", ["video/mp4", "image/png"])
    True
    >>> is_supported_type("image/png", ["text/png", "image/png"])
    True
    >>> is_supported_type("image/png", ["*"])
    True
    >>> is_supported_type("text/csv", ["application/csv", "application/json"])
    False

    :param content_type: tested type
    :param supported: collection of supported types

    """

    return bool(
        content_type
        and supported
        and any(st in ("*", content_type) for st in supported)
    )


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
    >>>             for chunk in reader:
    >>>                 dest.write(chunk)
    >>>         return FileData(
    >>>             location, size=upload.size,
    >>>             content_type=upload.content_type,
    >>>             hash=reader.get_hash(),
    >>>             algorithm=self.storage.settings.hashing_algorithm,
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

    storage: Storage

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
    collected from CKAN config file and exposes them to storage and its services.

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
    max_size: int = -1
    """Max allowed size of the upload"""
    public: bool = False
    """Whether storage is public and allows unauthenticated access."""


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
        declaration.declare(key.max_size, -1).append_validators(
            "parse_filesize",
        ).set_description(
            "The maximum size of a single upload."
            + "\nSupports size suffixes: 42B, 2M, 24KiB, 1GB."
            + " `-1` or any other negative value means no restrictions.",
        ).set_example("10MB")

        declaration.declare_list(key.supported_types, None).set_description(
            "Space-separated list of supported MIME types."
        ).set_example("text/csv application/pdf image/jpeg")

        declaration.declare_bool(key.public).set_description(
            "Whether storage is public and allows unauthenticated access."
        )

        declaration.declare_bool(key.overwrite_existing, True).set_description(
            "If file already exists, replace it with new content."
            + "\nThis option can be ignored by certain adapters.",
        )

        declaration.declare_bool(key.initialize).set_description(
            "Prepare storage backend for uploads(create path, bucket, DB)."
            + " This option depends on\nthe adapter and can be ignored if an adapter"
            + " cannot safely initialize the storage path.\nAlways prefer manual"
            + " creation of location specified in the ``path`` option.",
        )

        declaration.declare(key.path, "").set_description(
            "Prefix for the file's location. The actual meaning of this option"
            + " depends on the adapter. \nFS adapter uses the path as a root folder for"
            + " uploads. \nCloud adapters, usually, use path as a prefix for the name"
            + " of uploaded objects.",
        )

        declaration.declare(key.name, key[-1]).set_description(
            "Descriptive name of the storage used for debugging.\nWhen empty,"
            + " name from the config option is used,"
            + " i.e: `ckanext.files.storage.DEFAULT_NAME...`",
        )

        declaration.declare(key.hashing_algorithm, "md5").set_description(
            "Hashing algorithm used to calculate file's hash. This option is used by"
            " uploaders to calculate\nfile's hash and store it in FileData. Supported"
            " values depend on the implementation\nof the uploader, but common"
            " algorithms are: `md5`, `sha1`, `sha256`.\nIf storage adapter does not"
            " support customization of algorithm, it will ignore this option.\nFileData"
            " object produced by storage's ``upload`` method should contain the actual"
            " algorithm\nused to compute the hash."
        )

        declaration.declare_list(key.location_transformers, None).set_description(
            "List of transformations applied to the file location."
            "\nDepending on the storage type, sanitizing the path or removing"
            " special characters can be sensible.\nEmpty value leaves location"
            " unchanged, `uuid4` transforms location into UUIDv4,"
            "\n`uuid4_with_extension` transforms filename into UUIDv4 and appends"
            " original file's extension to it.\nCustom location transformers can be"
            "  registered via ``files_get_location_transformers`` \nmethod of"
            " ``IFiles`` interface.",
        ).set_example("datetime_prefix")

        declaration.declare_list(key.disabled_capabilities, None).set_description(
            "Capabilities that are not supported even if implemented."
            "\nCan be used to transform fully-featured storage into a"
            " read-only/write-only storage."
        )

    def as_response(
        self,
        data: FileData,
        filename: str | None = None,
        /,
        send_inline: bool = False,
        **kwargs: Any,
    ) -> types.Response:
        """Make Flask response with file attachment.

        By default, files are served as attachments and are downloaded as
        result. Use :ref:`ckan.files.inline_content_types` config option to
        specify content types that must be served inline. For example,
        following config option will render images, videos and text files in
        browser instead of forcing download::

            ckan.files.inline_content_types = image text/plain video

        If rendering is safe and preferable for individual call, enable
        ``send_inline`` flag.

        If either ``send_inline`` is set to ``True``, or file has content type
        that matches :ref:`ckan.files.inline_content_types`, it will be
        rendered on the page. Otherwise it will be sent as an attachment and
        downloaded by the client.

        :param data: file details
        :param filename: expected name of the file used instead of the real name
        :param send_inline: do not force download and try rendering file in browser

        :returns: Flask response with file's content

        """
        try:
            resp = self.reader.response(data, kwargs)
        except fk.exc.MissingFileError:
            return flask.Response(status=404)

        if "location" in resp.headers:
            return resp

        if "content-type" not in resp.headers:
            resp.headers["content-type"] = data.content_type

        if "content-length" not in resp.headers:
            resp.headers["content-length"] = data.size

        if "content-disposition" not in resp.headers:
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
        if max_size >= 0 and size > max_size:
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
    def permanent_link(self, data: FileData, /, **extras: dict[str, Any]) -> str | None:
        """Generate permanent link for the file."""
        from ckan.lib.helpers import helper_functions as h

        if link := super().permanent_link(data, **extras):
            return link

        if self.settings.public:
            return h.url_for(
                "file.public_download",
                storage_name=self.settings.name,
                location=data.location,
                _external=True,
            )
