from __future__ import annotations

from typing import Any, cast

import ckan.plugins as p
from ckan import authz, logic, model, types
from ckan.common import config, current_user
from ckan.types import AuthResult, Context


def _owner_allows(
    context: Context,
    owner_type: str,
    owner_id: str,
    operation: types.FileOwnerOperation,
) -> bool:
    """Decide if user is allowed to perform operation on the owner."""
    for plugin in p.PluginImplementations(p.IFiles):
        result = plugin.files_owner_allows(context, owner_type, owner_id, operation)
        if result is not None:
            return result

    if (
        operation == "file_transfer" and config["ckan.files.owner.transfer_as_update"]
    ) or (operation == "file_scan" and config["ckan.files.owner.scan_as_update"]):
        func_name = f"{owner_type}_update"

    else:
        func_name = f"{owner_type}_{operation}"

    result = authz.is_authorized(
        func_name, logic.fresh_context(context), {"id": owner_id}
    )
    return result["success"]


def _file_allows(
    context: Context,
    file: model.File,
    operation: types.FileOperation,
) -> bool:
    """Decide if user is allowed to perform operation on the file."""
    for plugin in p.PluginImplementations(p.IFiles):
        result = plugin.files_file_allows(context, file, operation)
        if result is not None:
            return result

    owner = file.owner

    if not owner:
        return False

    cascade = config["ckan.files.owner.cascade_access"]
    if owner.owner_type not in cascade:
        return False

    # `cascade` contains either empty list(aka "allow any storage") or list
    # with storage names that support cascade access.
    if cascade[owner.owner_type] and file.storage not in cascade[owner.owner_type]:
        return False

    func_name = f"{owner.owner_type}_{operation}"

    result = authz.is_authorized(
        func_name,
        logic.fresh_context(context),
        {"id": owner.owner_id},
    )

    return result["success"]


def _get_user(context: types.Context) -> model.User | None:
    """Get/cache the user object from the context."""
    user = context.get("auth_user_obj")
    if isinstance(user, model.User):
        return user

    if current_user and current_user.name == context["user"]:
        return cast(model.User, current_user)

    cache = logic.ContextCache(context)
    return cache.get("user", context["user"], lambda: model.User.get(context["user"]))


def _get_file(context: Context, file_id: str) -> model.File | None:
    """Get/cache the file object."""
    cache = logic.ContextCache(context)
    return cache.get_model("file", file_id, model.File)


# Permissions #################################################################


@logic.auth_allow_anonymous_access
def permission_manage_files(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to manage any file.

    This is a sort of "sysadmin" check in terms of file management. Give this
    permission to user who needs an access to every owned, unowned, hidden,
    incomplete and private file
    """
    return {"success": False, "msg": "Not allowed to manage files"}


@logic.auth_allow_anonymous_access
def permission_owns_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to manage a file.

    Normally, owner of the file passes this check as well as any user who has
    ``permission_manage_files``.
    """
    if authz.is_authorized_boolean("permission_manage_files", context, data_dict):
        return {"success": True}

    not_an_owner = "Not an owner of the file"
    user = _get_user(context)
    if not user:
        return {"success": False, "msg": not_an_owner}

    file = _get_file(context, data_dict["id"])
    if not file or not file.owner:
        return {"success": False, "msg": not_an_owner}

    return {
        "success": file.owner.owner_type == "user" and file.owner.owner_id == user.id,
        "msg": not_an_owner,
    }


@logic.auth_allow_anonymous_access
def permission_edit_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to edit a file.

    Owners and global managers can edit files. Additionally plugins can extend
    this permission via ``IFiles.files_file_allows`` hook.

    """
    result = authz.is_authorized_boolean("permission_owns_file", context, data_dict)

    if not result:
        file = _get_file(context, data_dict["id"])
        result = bool(file and _file_allows(context, file, "update"))

    return {"success": result, "msg": "Not allowed to edit file"}


@logic.auth_allow_anonymous_access
def permission_delete_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to delete the file.

    Owners and global managers can delete files. Additionally plugins can extend
    this permission via ``IFiles.files_file_allows`` hook.

    """
    result = authz.is_authorized_boolean("permission_owns_file", context, data_dict)
    if not result:
        file = _get_file(context, data_dict["id"])
        result = bool(file and _file_allows(context, file, "delete"))

    return {"success": result, "msg": "Not allowed to delete file"}


@logic.auth_allow_anonymous_access
def permission_read_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to read a file.

    Owners and global managers can read files. Additionally plugins can extend
    this permission via ``IFiles.files_file_allows`` hook.

    """
    result = authz.is_authorized_boolean("permission_owns_file", context, data_dict)
    if not result:
        file = _get_file(context, data_dict["id"])
        result = bool(file and _file_allows(context, file, "show"))

    return {"success": result, "msg": "Not allowed to read file"}


@logic.auth_allow_anonymous_access
def permission_download_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to download a file.

    Owners and global managers can download files. Additionally plugins can extend
    this permission via ``IFiles.files_file_allows`` hook.

    """
    result = authz.is_authorized_boolean("permission_read_file", context, data_dict)
    return {"success": result, "msg": "Not allowed to read file"}


# API #########################################################################


@logic.auth_allow_anonymous_access
def file_create(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user can upload a file.

    Files can be created by file managers by default. Config option
    ``ckan.files.authenticated_uploads.allow`` grants upload permission to
    every authenticated user, which may be reasonable as long as only trusted
    people can register the account.

    """
    if context["user"] and (
        config["ckan.files.authenticated_uploads.allow"]
        and data_dict["storage"] in config["ckan.files.authenticated_uploads.storages"]
    ):
        return {"success": True}

    return authz.is_authorized("permission_manage_files", context, data_dict)


@logic.auth_allow_anonymous_access
def file_register(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user can register files from storage in DB.

    Only file manager can register files.
    """
    return authz.is_authorized("permission_manage_files", context, data_dict)


@logic.auth_allow_anonymous_access
def file_search(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user can use global file search.

    Only file manager can search files. Publicly available files are exposed
    via combination of ownership and cascade access. There are no reasons to
    search through all the files for common visitor and this action should
    remain restricted.

    """
    return authz.is_authorized("permission_manage_files", context, data_dict)


@logic.auth_allow_anonymous_access
def file_delete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if file can be deleted."""
    return authz.is_authorized("permission_delete_file", context, data_dict)


@logic.auth_allow_anonymous_access
def file_show(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if file metadata can be viewed."""
    return authz.is_authorized("permission_read_file", context, data_dict)


@logic.auth_allow_anonymous_access
def file_rename(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if file can be renamed."""
    return authz.is_authorized("permission_edit_file", context, data_dict)


@logic.auth_allow_anonymous_access
def file_pin(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if file can be pinned to the current owner."""
    return authz.is_authorized("permission_edit_file", context, data_dict)


@logic.auth_allow_anonymous_access
def file_unpin(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if file can be unpinned from the current owner."""
    return authz.is_authorized("permission_edit_file", context, data_dict)


@logic.auth_allow_anonymous_access
def file_ownership_transfer(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if file ownership can be transfered to a different owner."""
    file = _get_file(context, data_dict["id"])
    if not file or (file.owner and file.owner.pinned and not data_dict["force"]):
        return {"success": False, "msg": "File is pinned"}

    result = authz.is_authorized_boolean("permission_manage_files", context, data_dict)
    if not result:
        result = bool(
            authz.is_authorized_boolean("permission_edit_file", context, data_dict)
            and _owner_allows(
                context,
                data_dict["owner_type"],
                data_dict["owner_id"],
                "file_transfer",
            ),
        )

    return {"success": result, "msg": "Not allowed to transfer ownership"}


@logic.auth_allow_anonymous_access
def file_owner_scan(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if list of all files of the owner is accessible."""
    result = authz.is_authorized_boolean("permission_manage_files", context, data_dict)
    if not result:
        result = _owner_allows(
            context,
            data_dict["owner_type"],
            data_dict["owner_id"],
            "file_scan",
        )

    return {"success": result, "msg": "Not allowed to list files"}
