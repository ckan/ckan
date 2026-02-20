"""File management API.

This module contains actions specific to the file domain.

The API defined here provides only a minimal, predictable set of operations
that are common to all supported storage backends. These operations are
deliberately limited to generic functionality (such as creating, reading,
updating, and deleting files) which can be implemented consistently across
different adapters without relying on storage-specific features.

It is important to note that modern storage systems often provide a rich set
of advanced capabilities — for example multipart and resumable uploads,
pre-signed URLs for controlled access, or native copy and move operations.
These are not exposed directly by this module, since their availability and
behavior vary significantly between storage providers.

Developers who require such advanced functionality are encouraged to build
custom APIs on top of this foundation, leveraging the underlying
`file-keeper <http://pypi.org/project/file-keeper>`_ library. That library
offers direct access to adapter-specific features while still keeping a
consistent abstraction layer. By combining the generic operations here with
the richer primitives provided by *file-keeper*, projects can tailor their
file management workflows to best match their storage backend.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError
from werkzeug.utils import secure_filename

from ckan import logic, model
from ckan.lib import files
from ckan.logic.schema import file as schema
from ckan.types import ActionResult, Context

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement
    from sqlalchemy.sql.schema import Column

log = logging.getLogger(__name__)


def _set_user_owner(context: Context, item_type: str, item_id: str):
    """Add user from context as file owner."""
    cache = logic.ContextCache(context)
    user = cache.get("user", context["user"], lambda: model.User.get(context["user"]))
    if user:
        owner = model.FileOwner(
            item_id=item_id,
            item_type=item_type,
            owner_id=user.id,
            owner_type="user",
        )
        context["session"].add(owner)


def _process_filters(  # noqa: C901
    filters: dict[str, Any], columns: Mapping[str, Column[Any]]
) -> ColumnElement[bool] | None:
    """Transform `{"$and":[{"field":{"$eq":"value"}}]}` filters into SQL filters."""

    items = []

    for k, v in filters.items():
        if k in ["$and", "$or"]:
            if not isinstance(v, list):
                raise logic.ValidationError(
                    {"filters": [f"Only lists are allowed inside {k}"]}
                )
            nested_items: list[ColumnElement[bool]] = []
            for sub_filters in v:
                if not isinstance(sub_filters, dict):
                    continue
                item = _process_filters(sub_filters, columns)
                if item is not None:
                    nested_items.append(item)

            if len(nested_items) > 1:
                wrapper = sa.and_ if k == "$and" else sa.or_
                items.append(wrapper(*nested_items).self_group())
            else:
                items.extend(nested_items)

        elif k in ["storage_data", "plugin_data"]:
            items.extend(_process_data(columns[k], v))

        elif k in columns:
            items.extend(_process_field(columns[k], v))

        else:
            raise logic.ValidationError({"filters": [f"Unknown filter: {k}"]})

    if not items:
        return

    if len(items) == 1:
        return items[0]

    return sa.and_(*items).self_group()


_op_map = {
    "$eq": "=",
    "$ne": "!=",
    "$lt": "<",
    "$lte": "<=",
    "$gt": ">",
    "$gte": ">=",
    "$in": "IN",
    "$is": "IS",
    "$isnot": "IS NOT",
    "$like": "LIKE",
    "$ilike": "ILIKE",
}


def _process_field(col: Column[Any], value: Any):  # noqa: C901
    """Transform `{"field":{"$eq":"value"}}` into SQL filters."""
    if isinstance(value, list):
        value = {"$in": value}

    elif value is None:
        value = {"$eq": None}

    elif not isinstance(value, dict):
        value = {"$eq": value}

    for operator, filter in value.items():
        column = col
        if operator not in _op_map:
            raise logic.ValidationError(
                {"filters": [f"Operator {operator} is not supported"]}
            )
        op = _op_map[operator]
        if filter is None:
            if op == "=":
                op = "is"
            elif op == "!=":
                op = "IS NOT"

        elif operator == "$in" and isinstance(filter, list):
            filter = tuple(filter)
        elif not isinstance(filter, col.type.python_type):
            filter = str(filter)
            column = sa.func.cast(column, sa.Text)

        func = column.bool_op(op)
        yield func(filter)


def _process_data(col: ColumnElement[Any], value: Any):  # pyright: ignore[reportUnknownParameterType]
    """Transform file/plugin data filters into SQL JSONB filters."""
    if not isinstance(value, dict):
        value = {"$eq": value}

    for k, v in value.items():
        if k in _op_map:
            op = _op_map[k]
            if v is None:
                if op == "=":
                    op = "is"
                elif op == "!=":
                    op = "IS NOT"

            if isinstance(v, bool):
                col = sa.cast(col, sa.Boolean)

            elif isinstance(v, int):
                col = sa.cast(col, sa.Integer)

            elif isinstance(v, float):
                col = sa.cast(col, sa.Float)

            else:
                col = col.astext

            yield col.bool_op(op)(v)

        else:
            yield from _process_data(col[k], v)


def _process_sort(
    sort: str | list[str] | list[list[str]] | Any,
    columns: Mapping[str, Column[Any]],
):
    """Transform sort field into SQL ordering statements."""
    if isinstance(sort, str):
        sort = [sort]

    for part in sort:
        if isinstance(part, str):
            field: str = part
            direction = "asc"

        elif isinstance(part, list) and len(part) == 2:
            field, direction = part

        else:
            raise logic.ValidationError({"sort": [f"Invalid sort value: {part}"]})

        if direction not in ["asc", "desc"]:
            raise logic.ValidationError(
                {"sort": [f"Invalid sort direction: {direction}"]}
            )

        if field not in columns:
            raise logic.ValidationError({"sort": [f"Invalid sort field: {field}"]})

        yield getattr(columns[field], direction)()


@logic.validate(schema.file_create)
def file_create(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileCreate:
    """Create a new file.

    The action passes uploaded file to the storage without strict
    validation. File is converted into standard upload object and everything
    else is controlled by storage. The same file may be accepted by one storage
    and rejected by another, depending on its configuration.

    The action is way too powerful to use it directly. The recommended approach
    is to register a different action for handling specific type of uploads and
    call the current action internally:

    .. code-block:: python

        def avatar_upload(context, data_dict):
            logic.check_access("avatar_upload", context, data_dict)
            storage = "avatars"
            name = context["user"] + ".jpeg"
            upload = data_dict["upload"]
            return tk.get_action("file_create")(
                Context(context, ignore_auth=True),
                {"name": name, "storage": storage, "upload": upload},
            )

    When uploading a real file(or using ``werkqeug.datastructures.FileStorage``),
    name parameter can be omited. In this case, the name of uploaded file is
    used:

    .. code-block:: sh

        $ ckanapi action file_create upload@path/to/file.txt

    When uploading a raw content of the file using bytes object, name is
    mandatory:

    .. code-block:: sh

        $ ckanapi action file_create upload@<(echo -n "hello world") name=file.txt

    .. note:: Requires storage with `CREATE` capability.

    :param name: human-readable name of the file.
        Defaults to filename of upload
    :type name: str, optional
    :param storage: name of the storage that will handle the upload.
        Defaults to the configured ``default`` storage.
    :type storage: str, optional
    :param upload: content of the file as bytes, file descriptor or uploaded file
    :type upload: bytes | file |
        :py:class:`~werkqeug.datastructures.FileStorage` |
        :py:class:`~ckan.lib.files.Upload`

    :returns: file details.

    """
    logic.check_access("file_create", context, data_dict)
    extras = data_dict.get("__extras", {})

    try:
        storage = files.get_storage(data_dict["storage"])
    except files.exc.UnknownStorageError as err:
        raise logic.ValidationError({"storage": [str(err)]}) from err

    if not storage.supports(files.Capability.CREATE):
        raise logic.ValidationError({"storage": ["Operation is not supported"]})

    if "name" not in data_dict:
        filename = data_dict["upload"].filename
        if not filename:
            msg = "Name is missing and cannot be deduced from upload"
            raise logic.ValidationError({"upload": [msg]})
        data_dict["name"] = filename

    filename = secure_filename(data_dict["name"])

    location = storage.prepare_location(filename, data_dict["upload"])
    stmt = model.File.by_location(location, data_dict["storage"])
    if fileobj := context["session"].scalar(stmt):
        raise logic.ValidationError({"upload": ["File already exists"]})

    try:
        storage_data = storage.upload(
            location,
            data_dict["upload"],
            ckan_api=extras,
        )
    except (files.exc.UploadError, files.exc.ExistingFileError) as err:
        raise logic.ValidationError({"upload": [str(err)]}) from err

    fileobj = model.File(
        name=filename,
        storage=data_dict["storage"],
        **storage_data.as_dict(),
    )
    context["session"].add(fileobj)

    _set_user_owner(context, "file", fileobj.id)

    # TODO: add hook to set plugin_data using extras

    if not context.get("defer_commit"):
        context["session"].commit()

    logic.ContextCache(context).set("file", fileobj.id, fileobj)

    return fileobj.dictize(context)


@logic.validate(schema.file_register)
def file_register(
    context: Context, data_dict: dict[str, Any]
) -> ActionResult.FileRegister:
    """Register untracked file from storage in DB.

    .. note:: Requires storage with `ANALYZE` capability.

    :param location: location of the file in the storage
    :type location: str, optional
    :param storage: name of the storage that will handle the upload.
        Defaults to the configured ``default`` storage.
    :type storage: str, optional

    :returns: file details.

    """
    logic.check_access("file_register", context, data_dict)

    try:
        storage = files.get_storage(data_dict["storage"])
    except files.exc.UnknownStorageError as err:
        raise logic.ValidationError({"storage": [str(err)]}) from err

    if not storage.supports(files.Capability.ANALYZE):
        raise logic.ValidationError({"storage": ["Operation is not supported"]})

    stmt = model.File.by_location(data_dict["location"], data_dict["storage"])
    if fileobj := context["session"].scalar(stmt):
        raise logic.ValidationError({"location": ["File is already registered"]})

    try:
        storage_data = storage.analyze(data_dict["location"])
    except files.exc.MissingFileError:
        raise logic.NotFound("file")

    fileobj = model.File(
        name=secure_filename(storage_data.location),
        storage=data_dict["storage"],
        **storage_data.as_dict(),
    )
    context["session"].add(fileobj)

    _set_user_owner(context, "file", fileobj.id)

    if not context.get("defer_commit"):
        context["session"].commit()

    logic.ContextCache(context).set("file", fileobj.id, fileobj)

    return fileobj.dictize(context)


def _file_search(  # noqa: C901, PLR0912, PLR0915
    context: Context,
    data_dict: dict[str, Any],
) -> ActionResult.FileSearch:
    """Search files.

    Provides an ability to search files according to [the future CKAN's search
    spec](https://github.com/ckan/ckan/discussions/8444).

    All columns of File model can be used as filters. Before the search, type
    of column and type of filter value are compared. If they are the same,
    original values are used in search. If type different, column value and
    filter value are casted to string.

    Even though results are usually not changed, using correct types leads to
    more efficient search.

    Apart from File columns, the following Owner properties can be used for
    searching: ``owner_id``, ``owner_type``, ``pinned``.

    :param start: index of first row in result/number of rows to skip. Default: `0`
    :type start: int, optional
    :param rows: number of rows to return. Default: `10`
    :type rows: int, optional
    :param sort: name of File column used for sorting. Default: `name`
    :type sort: str, optional
    :param filters: search filters
    :param filters: dict

    :returns: dictionary with `count` and `results`
    """
    context.setdefault("session", model.Session)
    data_dict.setdefault("sort", "name")
    data_dict.setdefault("filters", {})
    data_dict.setdefault("rows", 10)
    data_dict.setdefault("start", 0)
    columns = dict(**model.File.__table__.c, **model.FileOwner.__table__.c)

    stmt = sa.select(model.File).outerjoin(
        model.FileOwner,
        sa.and_(
            model.File.id == model.FileOwner.item_id,
            model.FileOwner.item_type == "file",
        ),
    )
    where = _process_filters(data_dict["filters"], columns)
    if where is not None:
        stmt = stmt.where(where)

    try:
        total: int = context["session"].scalar(stmt.with_only_columns(sa.func.count()))  # pyright: ignore[reportAssignmentType]
    except ProgrammingError:
        context["session"].rollback()
        msg = "Invalid file search request"
        log.exception(msg)
        raise logic.ValidationError({"filters": [msg]})

    for clause in _process_sort(data_dict["sort"], columns):
        stmt = stmt.order_by(clause)

    stmt = stmt.limit(data_dict["rows"]).offset(data_dict["start"])

    cache = logic.ContextCache(context)
    results: list[model.File] = [
        cache.set("file", f.id, f) for f in context["session"].scalars(stmt)
    ]
    return {"count": total, "results": [f.dictize(context) for f in results]}


@logic.validate(schema.file_delete)
def file_delete(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileDelete:
    """Remove file from storage.

    Unlike packages, file has no ``state`` field. Removal usually means that
    file details removed from DB and file itself removed from the storage.

    Some storage adapters can implement revisions of the file and keep archived
    versions or backups. Check storage adapter's documentation if you need to
    know whether there are chances that file is not completely removed with
    this operation.

    .. code-block:: sh

        $ ckanapi action file_delete id=226056e2-6f83-47c5-8bd2-102e2b82ab9a

    .. note:: Requires storage with `REMOVE` capability.

    :param id: ID of the file
    :type id: str

    :returns: details of the removed file.

    """
    logic.check_access("file_delete", context, data_dict)

    cache = logic.ContextCache(context)

    fileobj = cache.get_model("file", data_dict["id"], model.File)

    if not fileobj:
        raise logic.NotFound("file")

    file_data = files.FileData.from_object(fileobj)
    storage = files.get_storage(fileobj.storage)

    # If storage does not support EXISTS, we don't know whether file is present
    # in storage and have to try removal. If file exists in the storage,
    # removal it required.
    #
    # If neither of these is True(i.e., if we are sure, that file does not
    # exist in the storage because it was already removed), we can safely skip
    # removal from the storage and go directly to removal of the DB
    # record. Ideally, this should never happend, but to avoid locked records
    # in DB that point to non-existing file, because someone manually removed
    # it or formatted the drive, we are doing this check.
    if not storage.supports(files.Capability.EXISTS) or storage.exists(file_data):
        if not storage.supports(files.Capability.REMOVE):
            raise logic.ValidationError({"storage": ["Operation is not supported"]})

        try:
            storage.remove(file_data)
        except files.exc.PermissionError as err:
            raise logic.ValidationError({"storage": [str(err)]}) from err

    context["session"].delete(fileobj)

    if not context.get("defer_commit"):
        context["session"].commit()

    logic.ContextCache(context).invalidate("file", fileobj.id)

    return fileobj.dictize(context)


@logic.side_effect_free
@logic.validate(schema.file_show)
def file_show(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileShow:
    """Show file details.

    This action only displays information from DB record. There is no way to
    get the content of the file using this action(or any other API action).

    .. code-block:: sh

        $ ckanapi action file_show id=226056e2-6f83-47c5-8bd2-102e2b82ab9a

    :param id: ID of the file
    :type id: str

    :returns: file details
    """
    logic.check_access("file_show", context, data_dict)

    cache = logic.ContextCache(context)
    fileobj = cache.get_model("file", data_dict["id"], model.File)
    if not fileobj:
        raise logic.NotFound("file")

    return fileobj.dictize(context)


@logic.validate(schema.file_rename)
def file_rename(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileRename:
    """Rename the file.

    This action changes human-readable name of the file, which is stored in
    DB. Real location of the file in the storage is not modified.

    .. code-block:: sh

        $ ckanapi action file_show id=226056e2-6f83-47c5-8bd2-102e2b82ab9a \\
            name=new-name.txt

    :param id: ID of the file
    :type id: str
    :param name: new name of the file
    :type name: str

    :returns: file details
    """
    logic.check_access("file_rename", context, data_dict)

    cache = logic.ContextCache(context)
    fileobj = cache.get_model("file", data_dict["id"], model.File)
    if not fileobj:
        raise logic.NotFound("file")

    fileobj.name = secure_filename(data_dict["name"])

    if not context.get("defer_commit"):
        context["session"].commit()

    return fileobj.dictize(context)


@logic.validate(schema.file_pin)
def file_pin(context: Context, data_dict: dict[str, Any]) -> ActionResult.FilePin:
    """Pin file to the current owner.

    Pinned file cannot be transfered to a different owner. Use it to guarantee
    that file referred by entity is not accidentally transferred to a different
    owner.

    :param id: ID of the file
    :type id: str

    :returns: details of the pinned file
    """
    logic.check_access("file_pin", context, data_dict)

    cache = logic.ContextCache(context)
    fileobj = cache.get_model("file", data_dict["id"], model.File)
    if not fileobj:
        raise logic.NotFound("file")

    owner = fileobj.owner
    if not owner:
        raise logic.ValidationError({"id": ["File has no owner"]})

    owner.pinned = True

    if not context.get("defer_commit"):
        context["session"].commit()

    return fileobj.dictize(context)


@logic.validate(schema.file_unpin)
def file_unpin(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileUnpin:
    """Unpin file from the current owner.

    Unpinned file can be transfered to a different owner.

    :param id: ID of the file
    :type id: str

    :returns: details of the unpinned file
    """
    logic.check_access("file_unpin", context, data_dict)

    cache = logic.ContextCache(context)
    fileobj = cache.get_model("file", data_dict["id"], model.File)
    if not fileobj:
        raise logic.NotFound("file")

    if owner := fileobj.owner:
        owner.pinned = False

    if not context.get("defer_commit"):
        context["session"].commit()

    return fileobj.dictize(context)


@logic.validate(schema.ownership_transfer)
def file_ownership_transfer(
    context: Context, data_dict: dict[str, Any]
) -> ActionResult.FileOwnershipTransfer:
    """Transfer file ownership.

    Ownership determines required permissions to manage file. If file owned by
    a user, that user can see/modify/delete the file. If file owned by any
    other entity that supports :ref:`cascade access
    <ckan.files.owner.cascade_access>`, permissions regarding this entity
    determine file permissions.

    For example, if file owned by a package because its ``owner_type`` set to
    ``package`` and ``owner_id`` set to package's ID, whenever user performs an
    operation on the file, system checks if user can perform the same operation
    on the package. When user tries to read the file, system checks whether
    user can read the package; when user tries to delete the file, system
    checks whether user can delete the package. And result of this cascade
    checks determines success of the operation.

    ``owner_type`` is not restricted by existing entities. Anything that has
    corresponding auth functions(``<smth>_show``, ``<smth>_update``,
    ``<smth>_delete``) can be used as an owner. These functions will be called
    with ``id`` set to ``owner_id`` when cascade permission is checked.

    For example, to grant read access on the file to any user with the specific
    email domain, set the ``owner_type`` to ``email_domain`` and ``owner_id``
    to ``@specific.domain.com``. Then add ``email_domain`` to
    :ref:`ckan.files.owner.cascade_access` config option to enable cascade
    check for this owner type. Finally, register ``email_domain_show`` auth
    function that checks permissions:

    .. code-block:: python

        def email_domain_show(context, data_dict):
            email = context["auth_user_obj"]["email"]
            domain = data_dict["id"]
            return {
                "success": email.endswith(domain),
            }

    :param id: ID of the file upload
    :type id: str
    :param owner_id: ID of the new owner
    :type owner_id: str
    :param owner_type: type of the new owner
    :type owner_type: str
    :param force: move file even if it's pinned. Default: `False`
    :type force: bool
    :param pin: pin file after transfer to stop future transfers. Default: `False`
    :type pin: bool

    :returns: details of tranfered file

    """
    logic.check_access("file_ownership_transfer", context, data_dict)

    cache = logic.ContextCache(context)

    fileobj = cache.get_model("file", data_dict["id"], model.File)
    if not fileobj:
        raise logic.NotFound("file")

    if owner := fileobj.owner:
        if owner.pinned and not data_dict["force"]:
            raise logic.ValidationError(
                {
                    "force": ["Must be enabled to transfer pinned files"],
                },
            )
        elif (owner.owner_type, owner.owner_id) != (
            data_dict["owner_type"],
            data_dict["owner_id"],
        ):
            archive = model.FileOwnerTransferHistory.from_owner(owner, context["user"])
            context["session"].add(archive)

        owner.owner_id = data_dict["owner_id"]
        owner.owner_type = data_dict["owner_type"]

    else:
        owner = model.FileOwner(
            item_id=fileobj.id,
            item_type="file",
            owner_id=data_dict["owner_id"],
            owner_type=data_dict["owner_type"],
        )
        context["session"].add(owner)

    owner.pinned = data_dict["pin"]

    # without expiration SQLAlchemy fails to synchronize owner value during
    # transfer of unowned files
    context["session"].expire(fileobj, ["owner"])
    if not context.get("defer_commit"):
        context["session"].commit()

    return fileobj.dictize(context)


@logic.side_effect_free
@logic.validate(schema.owner_scan)
def file_owner_scan(
    context: Context, data_dict: dict[str, Any]
) -> ActionResult.FileOwnerScan:
    """List files of the owner.

    .. warning:: This action has hight probability to be changed or removed in
        future.

    This action requires ``<owner_type>_update`` permission when
    :ref:`ckan.files.owner.scan_as_update` is enabled and
    ``<owner_type>_file_scan`` otherwise.

    :param owner_id: ID of the owner
    :type owner_id: str
    :param owner_type: type of the owner
    :type owner_type: str
    :param start: index of first row in result/number of rows to skip.
    :type start: int, optional
    :param rows: number of rows to return.
    :type rows: int, optional
    :param sort: name of :py:class:`~ckan.model.File` column used for
        sorting. Default: ``name``
    :type sort: str, optional

    :returns: dictionary with `count` and `results`
    """
    if not data_dict["owner_id"] and data_dict["owner_type"] == "user":
        user = context.get("auth_user_obj")

        if isinstance(user, model.User) or (user := model.User.get(context["user"])):
            data_dict["owner_id"] = user.id

    logic.check_access("file_owner_scan", context, data_dict)

    data_dict["filters"] = {
        "owner_id": data_dict.pop("owner_id"),
        "owner_type": data_dict.pop("owner_type"),
    }
    return _file_search(context, data_dict)
