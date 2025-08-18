from __future__ import annotations


import ckan.plugins as p
from ckan import authz, model, logic, types
from ckan.common import config, current_user
from ckan.types import Context


def _owner_allows(
    context: Context,
    owner_type: str,
    owner_id: str,
    operation: types.FileOwnerOperation,
) -> bool:
    """Decide if user is allowed to perform operation on owner."""
    for plugin in p.PluginImplementations(p.IFiles):
        result = plugin.files_owner_allows(context, owner_type, owner_id, operation)
        if result is not None:
            return result

    if (
        operation == "file_transfer" and config["ckan.files.owner.transfer_as_update"]
    ) or (operation == "file_scan" and config["ckan.files.owner.transfer_as_update"]):
        func_name = f"{owner_type}_update"

    else:
        func_name = f"{owner_type}_{operation}"

    try:
        authz.is_authorized(func_name, logic.fresh_context(context), {"id": owner_id})

    except (logic.NotAuthorized, ValueError):
        return False

    return True


def _file_allows(
    context: Context,
    file: model.File,
    operation: types.FileOperation,
) -> bool:
    """Decide if user is allowed to perform operation on file."""
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

    if cascade[owner.owner_type] and file.storage not in cascade[owner.owner_type]:
        return False

    func_name = f"{owner.owner_type}_{operation}"

    try:
        authz.is_authorized(
            func_name,
            logic.fresh_context(context),
            {"id": owner.owner_id},
        )

    except (logic.NotAuthorized, ValueError):
        return False

    return True


def _get_user(context: Context) -> model.User | None:
    if "auth_user_obj" in context:
        return context["auth_user_obj"]

    user = current_user if current_user.is_authenticated else None
    username = context["user"]

    if user and username == user.name:
        return user

    cache = utils.ContextCache(context)
    return cache.get("user", username, lambda: model.User.get(username))


def _get_file(context: Context, file_id: str) -> model.File | None:
    cache = utils.ContextCache(context)
    return cache.get_model("file", file_id, model.File)
