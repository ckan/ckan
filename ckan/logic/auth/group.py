from __future__ import annotations

from typing import Optional

import ckan.authz as authz
import ckan.logic as logic
import ckan.logic.auth as logic_auth
from ckan.common import _, asbool, config
from ckan.logic.auth import get_group_object
from ckan.types import AuthResult, Context, DataDict


@logic.auth_allow_anonymous_access
def group_list(context: Context, data_dict: DataDict) -> AuthResult:
    # List of all active groups is visible by default
    return {"success": True}


@logic.auth_allow_anonymous_access
def group_list_authz(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized("group_list", context, data_dict)


@logic.auth_allow_anonymous_access
def group_show(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get("user")
    group = get_group_object(context, data_dict)
    if group.state == "active":
        if config.get("ckan.auth.public_user_details") or (
            not asbool(data_dict.get("include_users", False))
            and (data_dict.get("object_type", None) != "user")
        ):
            return {"success": True}
    authorized = authz.has_user_permission_for_group_or_org(group.id, user, "read")
    if authorized:
        return {"success": True}
    else:
        return {
            "success": False,
            "msg": _("User %s not authorized to read group %s") % (user, group.id),
        }


@logic.auth_allow_anonymous_access
def group_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized("group_list", context, data_dict)


@logic.auth_allow_anonymous_access
def member_roles_list(context: Context, data_dict: DataDict) -> AuthResult:
    return {"success": True}


@logic.auth_allow_anonymous_access
def group_package_show(context: Context, data_dict: DataDict) -> AuthResult:
    """Check if the set of datasets belonging to a group is visible.
    Visible to all by default."""
    return {"success": True}


@logic.auth_allow_anonymous_access
def member_list(context: Context, data_dict: DataDict) -> AuthResult:
    """Check if the members of a given group are visible.
    Visible to all by default."""
    return {"success": True}


def group_create(context: Context, data_dict: Optional[DataDict] = None) -> AuthResult:
    user = context["user"]
    user = authz.get_user_id_for_username(user, allow_none=True)

    if user and authz.check_config_permission("user_create_groups"):
        return {"success": True}
    return {
        "success": False,
        "msg": _("User %s not authorized to create groups") % user,
    }


def _group_or_org_member_create(context: Context, data_dict: DataDict) -> AuthResult:
    user = context["user"]
    group_id = data_dict["id"]
    if not authz.has_user_permission_for_group_or_org(group_id, user, "membership"):
        return {
            "success": False,
            "msg": _("User %s not authorized to add members") % user,
        }
    return {"success": True}


def group_member_create(context: Context, data_dict: DataDict) -> AuthResult:
    return _group_or_org_member_create(context, data_dict)


def member_create(context: Context, data_dict: DataDict) -> AuthResult:
    group = logic_auth.get_group_object(context, data_dict)
    user = context["user"]

    # User must be able to update the group to add a member to it
    permission = "update"
    # However if the user is member of group then they can add/remove datasets
    if not group.is_organization and data_dict.get("object_type") == "package":
        permission = "manage_group"

    authorized = authz.has_user_permission_for_group_or_org(group.id, user, permission)
    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to edit group %s") % (str(user), group.id),
        }
    else:
        return {"success": True}


def group_update(context: Context, data_dict: DataDict) -> AuthResult:
    group = logic_auth.get_group_object(context, data_dict)
    user = context["user"]
    authorized = authz.has_user_permission_for_group_or_org(group.id, user, "update")
    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to edit group %s") % (str(user), group.id),
        }
    else:
        return {"success": True}


def group_delete(context: Context, data_dict: DataDict) -> AuthResult:
    group = get_group_object(context, data_dict)
    user = context["user"]
    if not authz.check_config_permission("user_delete_groups"):
        return {
            "success": False,
            "msg": _("User %s not authorized to delete groups") % user,
        }
    authorized = authz.has_user_permission_for_group_or_org(group.id, user, "delete")
    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to delete group %s") % (user, group.id),
        }
    else:
        return {"success": True}


def group_purge(context: Context, data_dict: DataDict) -> AuthResult:
    # Only sysadmins are authorized to purge groups.
    return {"success": False}


def group_member_delete(context: Context, data_dict: DataDict) -> AuthResult:
    ## just return true as logic runs through member_delete
    return {"success": True}


def member_delete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized("member_create", context, data_dict)


def group_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized("group_update", context, data_dict)


@logic.auth_allow_anonymous_access
def group_list_available(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized("group_list", context, data_dict)


def group_change_state(context: Context, data_dict: DataDict) -> AuthResult:
    user = context["user"]
    group = logic_auth.get_group_object(context, data_dict)

    # use logic for group_update
    authorized = authz.is_authorized_boolean("group_update", context, data_dict)
    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to change state of group %s")
            % (str(user), group.id),
        }
    else:
        return {"success": True}


def group_edit_permissions(context: Context, data_dict: DataDict) -> AuthResult:
    user = context["user"]
    group = logic_auth.get_group_object(context, data_dict)

    authorized = authz.has_user_permission_for_group_or_org(group.id, user, "update")

    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to edit permissions of group %s")
            % (str(user), group.id),
        }
    else:
        return {"success": True}
