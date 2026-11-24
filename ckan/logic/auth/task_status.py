from __future__ import annotations

import ckan.logic as logic
from ckan.common import _
from ckan.types import AuthResult, Context, DataDict


@logic.auth_allow_anonymous_access
def task_status_show(context: Context, data_dict: DataDict) -> AuthResult:
    return {"success": True}


def task_status_update(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    user = context["user"]
    return {
        "success": False,
        "msg": _("User %s not authorized to update task_status table") % user,
    }


def task_status_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {"success": False}
