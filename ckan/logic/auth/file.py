from __future__ import annotations

from typing import Any, cast

import ckan.plugins as p
from ckan import authz, model, logic, types
from ckan.common import config
from ckan.types import AuthResult, Context


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
        authz.is_authorized(
            func_name,
            logic.fresh_context(context),
            {"id": owner_id},
        )

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

    owner = file.owner if file else None

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
