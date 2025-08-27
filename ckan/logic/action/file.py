"""File managemeng API.

This module contains actions specific to the file domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from collections.abc import Iterable, Mapping
from typing import Any

from ckan.types import Context, ActionResult
from ckan import logic, model
from ckan.logic.schema import file as schema

from ckan.lib import files
from werkzeug.utils import secure_filename

if TYPE_CHECKING:
    from sqlalchemy.sql.schema import Column
    from sqlalchemy.sql.elements import ColumnElement


def _set_user_owner(context: Context, item_type: str, item_id: str):
    """Add user from context as file owner."""
    cache = logic.ContextCache(context)
    user = cache.get("user", context["user"], lambda: model.User.get(context["user"]))
    if user:
        owner = model.Owner(
            item_id=item_id,
            item_type=item_type,
            owner_id=user.id,
            owner_type="user",
        )
        context["session"].add(owner)


def _process_filters(  # noqa: C901
    filters: dict[str, Any], columns: Mapping[str, Column[Any]]
) -> Iterable[ColumnElement[bool]]:
    for k, v in filters.items():
        if k == "$and":
            if not isinstance(v, list):
                raise logic.ValidationError(
                    {"filters": ["Only lists are allowed inside $and"]}
                )
            clauses = [
                element
                for sub_filters in v
                if isinstance(sub_filters, dict)
                for element in _process_filters(sub_filters, columns)
            ]
            if clauses:
                yield sa.and_(*clauses)

        elif k == "$or":
            if not isinstance(v, list):
                raise logic.ValidationError(
                    {"filters": ["Only lists are allowed inside $or"]}
                )

            clauses = [
                element
                for sub_filters in v
                if isinstance(sub_filters, dict)
                for element in _process_filters(sub_filters, columns)
            ]
            if clauses:
                yield sa.or_(*clauses)

        elif k in ["storage_data", "plugin_data"]:
            clauses = list(_process_data(columns[k], v))
            if clauses:
                yield sa.and_(*clauses)

        elif k in columns:
            clauses = list(
                _process_field(
                    columns[k],
                    v,
                )
            )
            if clauses:
                yield sa.and_(*clauses)


_op_map = {
    "$eq": "=",
    "$ne": "!=",
    "$lt": "<",
    "$lte": "<=",
    "$gt": ">",
    "$gte": ">=",
    "$in": "IN",
}


def _process_field(col: Column[Any], value: Any):
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

        elif not isinstance(value, col.type.python_type):
            filter = str(filter)
            column = sa.func.cast(column, sa.Text)

        yield column.bool_op(op)(filter)


def _process_data(col: ColumnElement[Any], value: Any):  # pyright: ignore[reportUnknownParameterType]
    if not isinstance(value, dict):
        raise logic.ValidationError(
            {"filters": ["Only dictionaries can be used to filter data fields"]}
        )

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

            else:
                col = col.astext

            yield col.bool_op(op)(v)
        else:
            yield from _process_data(col[k], v)


@logic.validate(schema.file_create)
def file_create(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileCreate:
    """Create a new file.

    The action passes uploaded file to the storage without strict
    validation. File is converted into standard upload object and everything
    else is controlled by storage. The same file may be accepted by one storage
    and rejected by another, depending on its configuration.

    The action is way too powerful to use it directly. The recommended approach
    is to register a different action for handling specific type of uploads and
    call the current action internally::

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
    used::

        ckanapi action file_create upload@path/to/file.txt

    When uploading a raw content of the file using bytes object, name is
    mandatory::

        ckanapi action file_create upload@<(echo -n "hello world") name=file.txt

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

    sess = context["session"]
    location = storage.prepare_location(filename, data_dict["upload"])
    stmt = model.File.by_location(location, data_dict["storage"])
    if fileobj := sess.scalar(stmt):
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
    sess.add(fileobj)

    _set_user_owner(context, "file", fileobj.id)

    # TODO: add hook to set plugin_data using extras

    if not context.get("defer_commit"):
        sess.commit()

    logic.ContextCache(context).set("file", fileobj.id, fileobj)

    return fileobj.dictize(context)


@logic.side_effect_free
@logic.validate(schema.file_search)
def file_search(  # noqa: C901, PLR0912, PLR0915
    context: Context,
    data_dict: dict[str, Any],
) -> ActionResult.FileSearch:
    """Search files.

    .. note:: This action is not stabilized yet and will change in future.

    Provides an ability to search files according to [the future CKAN's search
    spec](https://github.com/ckan/ckan/discussions/8444).

    All columns of File model can be used as filters. Before the search, type
    of column and type of filter value are compared. If they are the same,
    original values are used in search. If type different, column value and
    filter value are casted to string.

    This request produces ``size = 10`` SQL expression::

        ckanapi action file_search filters:'{"size": 10}'

    This request produces ``size::text = '10'`` SQL expression::

        ckanapi action file_search filters:'{"size": "10"}'

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
    logic.check_access("file_search", context, data_dict)

    sess = context["session"]

    stmt = sa.select(model.File).outerjoin(
        model.Owner,
        sa.and_(model.File.id == model.Owner.item_id, model.Owner.item_type == "file"),
    )

    columns = dict(**model.File.__table__.c, **model.Owner.__table__.c)

    for clause in _process_filters({"$and": [data_dict["filters"]]}, columns):
        stmt = stmt.where(clause)

    total: int = sess.scalar(stmt.with_only_columns(sa.func.count()))  # pyright: ignore[reportAssignmentType]

    sort_clauses = []
    sort = data_dict["sort"]
    if isinstance(sort, str):
        sort = [sort]

    for part in sort:
        if isinstance(part, str):
            field = part
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
        sort_clauses.append(getattr(columns[field], direction)())

    if sort_clauses:
        stmt = stmt.order_by(*sort_clauses)

    stmt = stmt.limit(data_dict["rows"]).offset(data_dict["start"])

    cache = logic.ContextCache(context)
    results: list[model.File] = [cache.set("file", f.id, f) for f in sess.scalars(stmt)]
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

    Example::

        ckanapi action file_delete id=226056e2-6f83-47c5-8bd2-102e2b82ab9a

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

    storage = files.get_storage(fileobj.storage)
    if not storage.supports(files.Capability.REMOVE):
        raise logic.ValidationError({"storage": ["Operation is not supported"]})

    try:
        storage.remove(files.FileData.from_object(fileobj))
    except files.exc.PermissionError as err:
        raise logic.ValidationError({"storage": [str(err)]}) from err

    sess = context["session"]
    sess.delete(fileobj)

    if not context.get("defer_commit"):
        sess.commit()

    logic.ContextCache(context).invalidate("file", fileobj.id)

    return fileobj.dictize(context)


@logic.side_effect_free
@logic.validate(schema.file_show)
def file_show(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileShow:
    """Show file details.

    This action only displays information from DB record. There is no way to
    get the content of the file using this action(or any other API action).

    Example::

        ckanapi action file_show id=226056e2-6f83-47c5-8bd2-102e2b82ab9a

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

    Example::

        ckanapi action file_show id=226056e2-6f83-47c5-8bd2-102e2b82ab9a \\
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
    sess = context["session"]

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
            archive = model.OwnerTransferHistory.from_owner(owner, context["user"])
            sess.add(archive)

        owner.owner_id = data_dict["owner_id"]
        owner.owner_type = data_dict["owner_type"]
        owner.pinned = data_dict["pin"]

    else:
        owner = model.Owner(
            item_id=fileobj.id,
            item_type="file",
            owner_id=data_dict["owner_id"],
            owner_type=data_dict["owner_type"],
        )
        sess.add(owner)

    owner.pinned = data_dict["pin"]

    sess.expire(fileobj)

    if not context.get("defer_commit"):
        sess.commit()

    return fileobj.dictize(context)


@logic.side_effect_free
@logic.validate(schema.owner_scan)
def file_owner_scan(
    context: Context, data_dict: dict[str, Any]
) -> ActionResult.FileOwnerScan:
    """List files of the owner.

    :param owner_id: ID of the owner
    :type owner_id: str
    :param owner_type: type of the owner
    :type owner_type: str
    :param start: index of first row in result/number of rows to skip.
    :type start: int, optional
    :param rows: number of rows to return.
    :type rows: int, optional
    :param sort: name of File column used for sorting. Default: `name`
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
    return logic.get_action("file_search")({"ignore_auth": True}, data_dict)
