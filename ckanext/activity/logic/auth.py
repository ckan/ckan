# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

import ckan.authz as authz
import ckan.plugins.toolkit as tk
from ckan.types import Context, DataDict, AuthResult

from ..model import Activity


def _get_activity_object(
    context: Context, data_dict: Optional[DataDict] = None
) -> Activity:
    try:
        return context["activity"]
    except KeyError:
        if not data_dict:
            data_dict = {}
        id = data_dict.get("id", None)
        if not id:
            raise tk.ValidationError(
                {"message": "Missing id, can not get Activity object"}
            )
        obj = Activity.get(id)
        if not obj:
            raise tk.ObjectNotFound()
        # Save in case we need this again during the request
        context["activity"] = obj
        return obj


def send_email_notifications(
    context: Context, data_dict: DataDict
) -> AuthResult:
    # Only sysadmins are authorized to send email notifications.
    return {"success": False}


def activity_create(context: Context, data_dict: DataDict) -> AuthResult:
    return {"success": False}


@tk.auth_allow_anonymous_access
def dashboard_activity_list(
    context: Context, data_dict: DataDict
) -> AuthResult:
    # FIXME: context['user'] could be an IP address but that case is not
    # handled here. Maybe add an auth helper function like is_logged_in().
    if context.get("user"):
        return {"success": True}
    else:
        return {
            "success": False,
            "msg": tk._("You must be logged in to access your dashboard."),
        }


@tk.auth_allow_anonymous_access
def dashboard_new_activities_count(
    context: Context, data_dict: DataDict
) -> AuthResult:
    # FIXME: This should go through check_access() not call is_authorized()
    # directly, but wait until 2939-orgs is merged before fixing this.
    # This is so a better not authourized message can be sent.
    return authz.is_authorized("dashboard_activity_list", context, data_dict)


@tk.auth_allow_anonymous_access
def activity_list(context: Context, data_dict: DataDict) -> AuthResult:
    """
    :param id: the id or name of the object (e.g. package id)
    :type id: string
    :param object_type: The type of the object (e.g. 'package', 'organization',
                        'group', 'user')
    :type object_type: string
    :param include_data: include the data field, containing a full object dict
        (otherwise the data field is only returned with the object's title)
    :type include_data: boolean
    """
    if data_dict["object_type"] not in (
        "package",
        "organization",
        "group",
        "user",
    ):
        return {"success": False, "msg": "object_type not recognized"}
    is_public = authz.check_config_permission("public_activity_stream_detail")
    if data_dict.get("include_data") and not is_public:
        # The 'data' field of the activity is restricted to users who are
        # allowed to edit the object
        show_or_update = "update"
    else:
        # the activity for an object (i.e. the activity metadata) can be viewed
        # if the user can see the object
        show_or_update = "show"
    action_on_which_to_base_auth = "{}_{}".format(
        data_dict["object_type"], show_or_update
    )  # e.g. 'package_update'
    return authz.is_authorized(
        action_on_which_to_base_auth, context, {"id": data_dict["id"]}
    )


@tk.auth_allow_anonymous_access
def user_activity_list(context: Context, data_dict: DataDict) -> AuthResult:
    data_dict["object_type"] = "user"
    # TODO: use authz.is_authorized in order to allow chained auth functions.
    # TODO: fix the issue in other functions as well
    return activity_list(context, data_dict)


@tk.auth_allow_anonymous_access
def package_activity_list(context: Context, data_dict: DataDict) -> AuthResult:
    data_dict["object_type"] = "package"
    return activity_list(context, data_dict)


@tk.auth_allow_anonymous_access
def group_activity_list(context: Context, data_dict: DataDict) -> AuthResult:
    data_dict["object_type"] = "group"
    return activity_list(context, data_dict)


@tk.auth_allow_anonymous_access
def organization_activity_list(
    context: Context, data_dict: DataDict
) -> AuthResult:
    data_dict["object_type"] = "organization"
    return activity_list(context, data_dict)


@tk.auth_allow_anonymous_access
def activity_show(context: Context, data_dict: DataDict) -> AuthResult:
    """
    :param id: the id of the activity
    :type id: string
    :param include_data: include the data field, containing a full object dict
        (otherwise the data field is only returned with the object's title)
    :type include_data: boolean
    """
    activity = _get_activity_object(context, data_dict)
    # NB it would be better to have recorded an activity_type against the
    # activity
    if "package" in activity.activity_type:
        object_type = "package"
    else:
        return {"success": False, "msg": "object_type not recognized"}
    return activity_list(
        context,
        {
            "id": activity.object_id,
            "include_data": data_dict["include_data"],
            "object_type": object_type,
        },
    )


@tk.auth_allow_anonymous_access
def activity_data_show(context: Context, data_dict: DataDict) -> AuthResult:
    """
    :param id: the id of the activity
    :type id: string
    """
    data_dict["include_data"] = True
    return activity_show(context, data_dict)


@tk.auth_allow_anonymous_access
def activity_diff(context: Context, data_dict: DataDict) -> AuthResult:
    """
    :param id: the id of the activity
    :type id: string
    """
    data_dict["include_data"] = True
    return activity_show(context, data_dict)


def dashboard_mark_activities_old(
    context: Context, data_dict: DataDict
) -> AuthResult:
    return authz.is_authorized("dashboard_activity_list", context, data_dict)
