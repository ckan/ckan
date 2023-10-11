# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import datetime
import json
from typing import Any, Optional

import ckan.plugins.toolkit as tk

from ckan.logic import validate
from ckan.types import Context, DataDict, ActionResult
import ckanext.activity.email_notifications as email_notifications

from . import schema
from ..model import activity as model_activity, activity_dict_save

log = logging.getLogger(__name__)


def send_email_notifications(
    context: Context, data_dict: DataDict
) -> ActionResult.SendEmailNotifications:
    """Send any pending activity stream notification emails to users.

    You must provide a sysadmin's API key/token in the Authorization header of
    the request, or call this action from the command-line via a `ckan notify
    send_emails ...` command.

    """
    tk.check_access("send_email_notifications", context, data_dict)

    if not tk.config.get("ckan.activity_streams_email_notifications"):
        raise tk.ValidationError(
            {
                "message": (
                    "ckan.activity_streams_email_notifications"
                    " is not enabled in config"
                )
            }
        )

    email_notifications.get_and_send_notifications_for_all_users()


def dashboard_mark_activities_old(
    context: Context, data_dict: DataDict
) -> ActionResult.DashboardMarkActivitiesOld:
    """Mark all the authorized user's new dashboard activities as old.

    This will reset
    :py:func:`~ckan.logic.action.get.dashboard_new_activities_count` to 0.

    """
    tk.check_access("dashboard_mark_activities_old", context, data_dict)
    model = context["model"]
    user_obj = model.User.get(context["user"])
    assert user_obj
    user_id = user_obj.id
    dashboard = model.Dashboard.get(user_id)
    if dashboard:
        dashboard.activity_stream_last_viewed = datetime.datetime.utcnow()
    if not context.get("defer_commit"):
        model.repo.commit()


def activity_create(
    context: Context, data_dict: DataDict
) -> Optional[dict[str, Any]]:
    """Create a new activity stream activity.

    You must be a sysadmin to create new activities.

    :param user_id: the name or id of the user who carried out the activity,
        e.g. ``'seanh'``
    :type user_id: string
    :param object_id: the name or id of the object of the activity, e.g.
        ``'my_dataset'``
    :param activity_type: the type of the activity, this must be an activity
        type that CKAN knows how to render, e.g. ``'new package'``,
        ``'changed user'``, ``'deleted group'`` etc.
    :type activity_type: string
    :param data: any additional data about the activity
    :type data: dictionary

    :returns: the newly created activity
    :rtype: dictionary

    """

    tk.check_access("activity_create", context, data_dict)

    if not tk.config.get("ckan.activity_streams_enabled"):
        return

    model = context["model"]

    # Any revision_id that the caller attempts to pass in the activity_dict is
    # ignored and removed here.
    if "revision_id" in data_dict:
        del data_dict["revision_id"]

    sch = context.get("schema") or schema.default_create_activity_schema()

    data, errors = tk.navl_validate(data_dict, sch, context)
    if errors:
        raise tk.ValidationError(errors)

    activity = activity_dict_save(data, context)

    if not context.get("defer_commit"):
        model.repo.commit()

    log.debug("Created '%s' activity" % activity.activity_type)
    return model_activity.activity_dictize(activity, context)


@validate(schema.default_activity_list_schema)
@tk.side_effect_free
def user_activity_list(
    context: Context, data_dict: DataDict
) -> list[dict[str, Any]]:
    """Return a user's public activity stream.

    You must be authorized to view the user's profile.


    :param id: the id or name of the user
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31`` unless set in site's configuration
        ``ckan.activity_list_limit``, upper limit: ``100`` unless set in
        site's configuration ``ckan.activity_list_limit_max``)
    :type limit: int
    :param after: After timestamp
        (optional, default: ``None``)
    :type after: int, str
    :param before: Before timestamp
        (optional, default: ``None``)
    :type before: int, str

    :rtype: list of dictionaries

    """
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    tk.check_access("user_activity_list", context, data_dict)

    model = context["model"]

    user_ref = data_dict.get("id")  # May be user name or id.
    user = model.User.get(user_ref)
    if user is None:
        raise tk.ObjectNotFound()

    offset = data_dict.get("offset", 0)
    limit = data_dict["limit"]  # defaulted, limited & made an int by schema
    after = data_dict.get("after")
    before = data_dict.get("before")

    activity_objects = model_activity.user_activity_list(
        user.id,
        limit=limit,
        offset=offset,
        after=after,
        before=before,
    )

    return model_activity.activity_list_dictize(activity_objects, context)


@validate(schema.default_activity_list_schema)
@tk.side_effect_free
def package_activity_list(
    context: Context, data_dict: DataDict
) -> list[dict[str, Any]]:
    """Return a package's activity stream (not including detail)

    You must be authorized to view the package.

    :param id: the id or name of the package
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31`` unless set in site's configuration
        ``ckan.activity_list_limit``, upper limit: ``100`` unless set in
        site's configuration ``ckan.activity_list_limit_max``)
    :type limit: int
    :param after: After timestamp
        (optional, default: ``None``)
    :type after: int, str
    :param before: Before timestamp
        (optional, default: ``None``)
    :type before: int, str
    :param include_hidden_activity: whether to include 'hidden' activity, which
        is not shown in the Activity Stream page. Hidden activity includes
        activity done by the site_user, such as harvests, which are not shown
        in the activity stream because they can be too numerous, or activity by
        other users specified in config option `ckan.hide_activity_from_users`.
        NB Only sysadmins may set include_hidden_activity to true.
        (default: false)
    :type include_hidden_activity: bool
    :param activity_types: A list of activity types to include in the response
    :type activity_types: list

    :param exclude_activity_types: A list of activity types to exclude from the
        response
    :type exclude_activity_types: list

    :rtype: list of dictionaries

    """
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    include_hidden_activity = data_dict.get("include_hidden_activity", False)
    activity_types = data_dict.pop("activity_types", None)
    exclude_activity_types = data_dict.pop("exclude_activity_types", None)

    if activity_types is not None and exclude_activity_types is not None:
        raise tk.ValidationError(
            {
                "activity_types": [
                    "Cannot be used together with `exclude_activity_types"
                ]
            }
        )

    tk.check_access("package_activity_list", context, data_dict)

    model = context["model"]

    package_ref = data_dict.get("id")  # May be name or ID.
    package = model.Package.get(package_ref)
    if package is None:
        raise tk.ObjectNotFound()

    offset = int(data_dict.get("offset", 0))
    limit = data_dict["limit"]  # defaulted, limited & made an int by schema
    after = data_dict.get("after")
    before = data_dict.get("before")

    activity_objects = model_activity.package_activity_list(
        package.id,
        limit=limit,
        offset=offset,
        after=after,
        before=before,
        include_hidden_activity=include_hidden_activity,
        activity_types=activity_types,
        exclude_activity_types=exclude_activity_types,
    )

    return model_activity.activity_list_dictize(activity_objects, context)


@validate(schema.default_activity_list_schema)
@tk.side_effect_free
def group_activity_list(
    context: Context, data_dict: DataDict
) -> list[dict[str, Any]]:
    """Return a group's activity stream.

    You must be authorized to view the group.

    :param id: the id or name of the group
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31`` unless set in site's configuration
        ``ckan.activity_list_limit``, upper limit: ``100`` unless set in
        site's configuration ``ckan.activity_list_limit_max``)
    :type limit: int
    :param include_hidden_activity: whether to include 'hidden' activity, which
        is not shown in the Activity Stream page. Hidden activity includes
        activity done by the site_user, such as harvests, which are not shown
        in the activity stream because they can be too numerous, or activity by
        other users specified in config option `ckan.hide_activity_from_users`.
        NB Only sysadmins may set include_hidden_activity to true.
        (default: false)
    :type include_hidden_activity: bool

    :rtype: list of dictionaries

    """
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    data_dict = dict(data_dict, include_data=False)
    include_hidden_activity = data_dict.get("include_hidden_activity", False)
    activity_types = data_dict.pop("activity_types", None)
    tk.check_access("group_activity_list", context, data_dict)

    group_id = data_dict.get("id")
    offset = data_dict.get("offset", 0)
    limit = data_dict["limit"]  # defaulted, limited & made an int by schema

    # Convert group_id (could be id or name) into id.
    group_show = tk.get_action("group_show")
    group_id = group_show(context, {"id": group_id})["id"]

    after = data_dict.get("after")
    before = data_dict.get("before")

    activity_objects = model_activity.group_activity_list(
        group_id,
        limit=limit,
        offset=offset,
        after=after,
        before=before,
        include_hidden_activity=include_hidden_activity,
        activity_types=activity_types
    )

    return model_activity.activity_list_dictize(activity_objects, context)


@validate(schema.default_activity_list_schema)
@tk.side_effect_free
def organization_activity_list(
    context: Context, data_dict: DataDict
) -> list[dict[str, Any]]:
    """Return a organization's activity stream.

    :param id: the id or name of the organization
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31`` unless set in site's configuration
        ``ckan.activity_list_limit``, upper limit: ``100`` unless set in
        site's configuration ``ckan.activity_list_limit_max``)
    :type limit: int
    :param include_hidden_activity: whether to include 'hidden' activity, which
        is not shown in the Activity Stream page. Hidden activity includes
        activity done by the site_user, such as harvests, which are not shown
        in the activity stream because they can be too numerous, or activity by
        other users specified in config option `ckan.hide_activity_from_users`.
        NB Only sysadmins may set include_hidden_activity to true.
        (default: false)
    :type include_hidden_activity: bool

    :rtype: list of dictionaries

    """
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    include_hidden_activity = data_dict.get("include_hidden_activity", False)
    tk.check_access("organization_activity_list", context, data_dict)

    org_id = data_dict.get("id")
    offset = data_dict.get("offset", 0)
    limit = data_dict["limit"]  # defaulted, limited & made an int by schema
    activity_types = data_dict.pop("activity_types", None)

    # Convert org_id (could be id or name) into id.
    org_show = tk.get_action("organization_show")
    org_id = org_show(context, {"id": org_id})["id"]

    after = data_dict.get("after")
    before = data_dict.get("before")

    activity_objects = model_activity.organization_activity_list(
        org_id,
        limit=limit,
        offset=offset,
        after=after,
        before=before,
        include_hidden_activity=include_hidden_activity,
        activity_types=activity_types
    )

    return model_activity.activity_list_dictize(activity_objects, context)


@validate(schema.default_dashboard_activity_list_schema)
@tk.side_effect_free
def recently_changed_packages_activity_list(
    context: Context, data_dict: DataDict
) -> list[dict[str, Any]]:
    """Return the activity stream of all recently added or changed packages.

    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31`` unless set in site's configuration
        ``ckan.activity_list_limit``, upper limit: ``100`` unless set in
        site's configuration ``ckan.activity_list_limit_max``)
    :type limit: int

    :rtype: list of dictionaries

    """
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    offset = data_dict.get("offset", 0)
    limit = data_dict["limit"]  # defaulted, limited & made an int by schema

    activity_objects = model_activity.recently_changed_packages_activity_list(
        limit=limit, offset=offset
    )

    return model_activity.activity_list_dictize(activity_objects, context)


@validate(schema.default_dashboard_activity_list_schema)
@tk.side_effect_free
def dashboard_activity_list(
    context: Context, data_dict: DataDict
) -> list[dict[str, Any]]:
    """Return the authorized (via login or API key) user's dashboard activity
       stream.

    Unlike the activity dictionaries returned by other ``*_activity_list``
    actions, these activity dictionaries have an extra boolean value with key
    ``is_new`` that tells you whether the activity happened since the user last
    viewed her dashboard (``'is_new': True``) or not (``'is_new': False``).

    The user's own activities are always marked ``'is_new': False``.

    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31`` unless set in site's configuration
        ``ckan.activity_list_limit``, upper limit: ``100`` unless set in
        site's configuration ``ckan.activity_list_limit_max``)
    :type limit: int

    :rtype: list of activity dictionaries

    """
    tk.check_access("dashboard_activity_list", context, data_dict)

    model = context["model"]
    user_obj = model.User.get(context["user"])
    assert user_obj
    user_id = user_obj.id
    offset = data_dict.get("offset", 0)
    limit = data_dict["limit"]  # defaulted, limited & made an int by schema
    before = data_dict.get("before")
    after = data_dict.get("after")
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    activity_objects = model_activity.dashboard_activity_list(
        user_id, limit=limit, offset=offset, before=before, after=after
    )

    activity_dicts = model_activity.activity_list_dictize(
        activity_objects, context
    )

    # Mark the new (not yet seen by user) activities.
    strptime = datetime.datetime.strptime
    fmt = "%Y-%m-%dT%H:%M:%S.%f"
    dashboard = model.Dashboard.get(user_id)
    last_viewed = None
    if dashboard:
        last_viewed = dashboard.activity_stream_last_viewed
    for activity in activity_dicts:
        if activity["user_id"] == user_id:
            # Never mark the user's own activities as new.
            activity["is_new"] = False
        elif last_viewed:
            activity["is_new"] = (
                strptime(activity["timestamp"], fmt) > last_viewed
            )

    return activity_dicts


@tk.side_effect_free
def dashboard_new_activities_count(
    context: Context, data_dict: DataDict
) -> ActionResult.DashboardNewActivitiesCount:
    """Return the number of new activities in the user's dashboard.

    Return the number of new activities in the authorized user's dashboard
    activity stream.

    Activities from the user herself are not counted by this function even
    though they appear in the dashboard (users don't want to be notified about
    things they did themselves).

    :rtype: int

    """
    tk.check_access("dashboard_new_activities_count", context, data_dict)
    activities = tk.get_action("dashboard_activity_list")(context, data_dict)
    return len([activity for activity in activities if activity["is_new"]])


@tk.side_effect_free
def activity_show(context: Context, data_dict: DataDict) -> dict[str, Any]:
    """Show details of an item of 'activity' (part of the activity stream).

    :param id: the id of the activity
    :type id: string

    :rtype: dictionary
    """
    model = context["model"]
    activity_id = tk.get_or_bust(data_dict, "id")

    activity = model.Session.query(model_activity.Activity).get(activity_id)
    if activity is None:
        raise tk.ObjectNotFound()
    context["activity"] = activity

    tk.check_access("activity_show", context, data_dict)

    activity = model_activity.activity_dictize(activity, context)
    return activity


@tk.side_effect_free
def activity_data_show(
    context: Context, data_dict: DataDict
) -> dict[str, Any]:
    """Show the data from an item of 'activity' (part of the activity
    stream).

    For example for a package update this returns just the dataset dict but
    none of the activity stream info of who and when the version was created.

    :param id: the id of the activity
    :type id: string
    :param object_type: 'package', 'user', 'group' or 'organization'
    :type object_type: string

    :rtype: dictionary
    """
    model = context["model"]
    activity_id = tk.get_or_bust(data_dict, "id")
    object_type = data_dict.get("object_type")

    activity = model.Session.query(model_activity.Activity).get(activity_id)
    if activity is None:
        raise tk.ObjectNotFound()
    context["activity"] = activity

    tk.check_access("activity_data_show", context, data_dict)

    activity = model_activity.activity_dictize(activity, context)
    try:
        activity_data = activity["data"]
    except KeyError:
        raise tk.ObjectNotFound("Could not find data in the activity")
    if object_type:
        try:
            activity_data = activity_data[object_type]
        except KeyError:
            raise tk.ObjectNotFound(
                "Could not find that object_type in the activity"
            )
    return activity_data


@tk.side_effect_free
def activity_diff(context: Context, data_dict: DataDict) -> dict[str, Any]:
    """Returns a diff of the activity, compared to the previous version of the
    object

    :param id: the id of the activity
    :type id: string
    :param object_type: 'package', 'user', 'group' or 'organization'
    :type object_type: string
    :param diff_type: 'unified', 'context', 'html'
    :type diff_type: string
    """
    import difflib

    model = context["model"]
    activity_id = tk.get_or_bust(data_dict, "id")
    object_type = tk.get_or_bust(data_dict, "object_type")
    diff_type = data_dict.get("diff_type", "unified")

    tk.check_access("activity_diff", context, data_dict)

    activity = model.Session.query(model_activity.Activity).get(activity_id)
    if activity is None:
        raise tk.ObjectNotFound()
    prev_activity = (
        model.Session.query(model_activity.Activity)
        .filter_by(object_id=activity.object_id)
        .filter(model_activity.Activity.timestamp < activity.timestamp)
        .order_by(
            # type_ignore_reason: incomplete SQLAlchemy types
            model_activity.Activity.timestamp.desc()  # type: ignore
        )
        .first()
    )
    if prev_activity is None:
        raise tk.ObjectNotFound("Previous activity for this object not found")
    activity_objs = [prev_activity, activity]
    try:
        objs = [
            activity_obj.data[object_type] for activity_obj in activity_objs
        ]
    except KeyError:
        raise tk.ObjectNotFound("Could not find object in the activity data")
    # convert each object dict to 'pprint'-style
    # and split into lines to suit difflib
    obj_lines = [
        json.dumps(obj, indent=2, sort_keys=True).split("\n") for obj in objs
    ]

    # do the diff
    if diff_type == "unified":
        # type_ignore_reason: typechecker can't predict number of items
        diff_generator = difflib.unified_diff(*obj_lines)  # type: ignore
        diff = "\n".join(line for line in diff_generator)
    elif diff_type == "context":
        # type_ignore_reason: typechecker can't predict number of items
        diff_generator = difflib.context_diff(*obj_lines)  # type: ignore
        diff = "\n".join(line for line in diff_generator)
    elif diff_type == "html":
        # word-wrap lines. Otherwise you get scroll bars for most datasets.
        import re

        for obj_index in (0, 1):
            wrapped_obj_lines = []
            for line in obj_lines[obj_index]:
                wrapped_obj_lines.extend(re.findall(r".{1,70}(?:\s+|$)", line))
            obj_lines[obj_index] = wrapped_obj_lines
        # type_ignore_reason: typechecker can't predict number of items
        diff = difflib.HtmlDiff().make_table(*obj_lines)  # type: ignore
    else:
        raise tk.ValidationError({"message": "diff_type not recognized"})

    activities = [
        model_activity.activity_dictize(activity_obj, context)
        for activity_obj in activity_objs
    ]

    return {
        "diff": diff,
        "activities": activities,
    }
