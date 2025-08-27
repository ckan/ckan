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

    .. note: Requires storage with `CREATE` capability.

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
    :type start: int, optional
    :param rows: number of rows to return. Default: `10`
    :type rows: int, optional
    :param sort: name of File column used for sorting. Default: `name`
    :type sort: str, optional
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

    .. note: Requires storage with `REMOVE` capability.

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

    return logic.get_action("file_search")({"ignore_auth": True}, data_dict)
