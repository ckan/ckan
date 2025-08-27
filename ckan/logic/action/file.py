"""File managemeng API.

This module contains actions specific to the file domain.
"""
from __future__ import annotations

from typing import cast
import sqlalchemy as sa
from typing import Any
from ckan.types import Context, ActionResult
from ckan import logic, model
from ckan.logic.schema import file as schema

from ckan.lib import files
from werkzeug.utils import secure_filename


def _set_user_owner(context: Context, item_type: str, item_id: str):
    """Add user from context as file owner."""
    user = model.User.get(context.get("user", ""))
    if user:
        owner = model.Owner(
            item_id=item_id,
            item_type=item_type,
            owner_id=user.id,
            owner_type="user",
        )
        context["session"].add(owner)


def _flat_mask(data: dict[str, Any]) -> dict[tuple[Any, ...], Any]:
    result: dict[tuple[Any, ...], Any] = {}

    for k, v in data.items():
        if isinstance(v, dict):
            result.update({(k,) + sk: sv for sk, sv in _flat_mask(v).items()})
        else:
            result[(k,)] = v

    return result


@logic.validate(schema.file_create)
def file_create(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileCreate:
    """Create a new file.

    .. note: Requires storage with `CREATE` capability.

    The action passes uploaded file to the storage without strict
    validation. File is converted into standard upload object and everything
    else is controlled by storage. The same file may be accepted by one storage
    and rejected by another, depending on its configuration.

    The action is way too powerful to use it directly. The recommended approach
    is to register a different action for handling specific type of uploads and
    call the current action internally::

        def avatar_upload(context, data_dict):
            tk.check_access("avatar_upload", context, data_dict)
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

    try:
        storage_data = storage.upload(
            storage.prepare_location(filename, data_dict["upload"]),
            data_dict["upload"],
            **extras,
        )
    except (files.exc.UploadError, files.exc.ExistingFileError) as err:
        raise logic.ValidationError({"upload": [str(err)]}) from err

    fileobj = model.File(
        name=filename,
        location="",
        storage=data_dict["storage"],
    )
    storage_data.into_object(fileobj)
    sess = context["session"]
    sess.add(fileobj)

    _set_user_owner(context, "file", fileobj.id)
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

    .. note: This action is not stabilized yet and will change in future.

    Provides an ability to search files using exact filter by name,
    content_type, size, owner, etc. Results are paginated and returned in
    package_search manner, as dict with `count` and `results` items.

    All columns of File model can be used as filters. Before the search, type
    of column and type of filter value are compared. If they are the same,
    original values are used in search. If type different, column value and
    filter value are casted to string.

    This request produces `size = 10` SQL expression:

        ckanapi action file_search size:10

    This request produces `size::text = '10'` SQL expression:

        ckanapi action file_search size=10

    Even though results are usually not changed, using correct types leads to
    more efficient search.

    Apart from File columns, the following Owner properties can be used for
    searching: `owner_id`, `owner_type`, `pinned`.

    `storage_data` and `plugin_data` are dictionaries. Filter's value for these
    fields used as a mask. For example, `storage_data={"a": {"b": 1}}` matches
    any File with `storage_data` *containing* item `a` with value that contains
    `b=1`. This works only with data represented by nested dictionaries,
    without other structures, like list or sets.

    Experimental feature: File columns can be passed as a pair of operator and
    value. This feature will be replaced by strictly defined query language at
    some point:

        ckanapi action file_search
            size:'["<", 100]' content_type:'["like", "text/%"]'

    Fillowing operators are accepted: `=`, `<`, `>`, `!=`, `like`

    :param start: index of first row in result/number of rows to skip. Default: `0`
    :param rows: number of rows to return. Default: `10`
    :param sort: name of File column used for sorting. Default: `name`
    :param reverse: sort results in descending order. Default: `False`
    :param storage_data: mask for `storage_data` column. Default: `{}`
    :param plugin_data: mask for `plugin_data` column. Default: `{}`
    :param owner_id: show only specific owner id if present. Default: `None`
    :param owner_type: show only specific owner type if present. Default: `None`
    :param pinned: show only pinned/unpinned items if present. Default: `None`
    :param completed: use `False` to search incomplete uploads. Default: `True`

    :returns: dictionary with `count` and `results`
    """

    logic.check_access("file_search", context, data_dict)

    sess = context["session"]

    stmt = sa.select(model.File).outerjoin(
        model.Owner,
        sa.and_(model.File.id == model.Owner.item_id, model.Owner.item_type == "file"),
    )

    inspector = sa.inspect(model.File)

    for field in ["owner_type", "owner_id", "pinned"]:
        if field in data_dict:
            value = data_dict[field]
            if value is not None and not (
                field == "pinned" and isinstance(value, bool)
            ):
                value = str(value)
            stmt = stmt.where(getattr(model.Owner, field) == value)

    columns = inspector.columns  # pyright: ignore[reportOptionalMemberAccess]

    for mask in ["storage_data", "plugin_data"]:
        if mask in data_dict:
            for k, v in _flat_mask(data_dict[mask]).items():
                field = columns[mask]
                for segment in k:
                    field = field[segment]

                stmt = stmt.where(field.astext == v)

    for k, v in data_dict.get("__extras", {}).items():
        if k not in columns:
            continue

        if (
            isinstance(v, list)
            and len(v) == 2  # noqa: PLR2004
            and v[0] in ["=", "<", ">", "!=", "like"]
        ):
            op, v = cast("list[Any]", v)  # noqa: PLW2901
        else:
            op = "="

        col = columns[k]
        column_type = col.type.python_type
        if not isinstance(v, column_type) and v is not None:
            v = str(v)  # noqa: PLW2901
            col = sa.func.cast(col, sa.Text)

        if v is None:
            if op == "=":
                op = "is"
            elif op == "!=":
                op = "is not"

        stmt = stmt.where(col.bool_op(op)(v))

    total = sess.scalar(stmt.with_only_columns(sa.func.count()))

    parts = data_dict["sort"].split(".")
    sort = parts[0]
    sort_path = parts[1:]

    if sort not in columns:
        raise logic.ValidationError({"sort": ["Unknown sort column"]})

    column = columns[sort]

    if sort_path and sort == "storage_data":
        for part in sort_path:
            column = column[part]

    if data_dict["reverse"]:
        column = column.desc()

    stmt = stmt.order_by(column)

    stmt = stmt.limit(data_dict["rows"]).offset(data_dict["start"])

    cache = logic.ContextCache(context)
    results: list[model.File] = [cache.set("file", f.id, f) for f in sess.scalars(stmt)]
    return {"count": total, "results": [f.dictize(context) for f in results]}


def file_delete(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileDelete:
    return {}


def file_show(context: Context, data_dict: dict[str, Any]) -> ActionResult.FileShow: ...


def file_rename(
    context: Context, data_dict: dict[str, Any]
) -> ActionResult.FileRename: ...


def file_pin(context: Context, data_dict: dict[str, Any]) -> ActionResult.FilePin: ...


def file_unpin(
    context: Context, data_dict: dict[str, Any]
) -> ActionResult.FileUnpin: ...


def file_ownership_transfer(
    context: Context, data_dict: dict[str, Any]
) -> ActionResult.FileOwnershipTransfer: ...


def file_owner_scan(
    context: Context, data_dict: dict[str, Any]
) -> ActionResult.FileOwnerScan: ...
