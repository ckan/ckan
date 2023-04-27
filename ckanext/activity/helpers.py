# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Any, Optional, cast

import jinja2
import datetime
from markupsafe import Markup

import ckan.model as model
import ckan.plugins.toolkit as tk

from ckan.types import Context
from . import changes


def dashboard_activity_stream(
    user_id: str,
    filter_type: Optional[str] = None,
    filter_id: Optional[str] = None,
    offset: int = 0,
    limit: int = 0,
    before: Optional[datetime.datetime] = None,
    after: Optional[datetime.datetime] = None,
) -> list[dict[str, Any]]:
    """Return the dashboard activity stream of the current user.

    :param user_id: the id of the user
    :type user_id: string

    :param filter_type: the type of thing to filter by
    :type filter_type: string

    :param filter_id: the id of item to filter by
    :type filter_id: string

    :returns: an activity stream as an HTML snippet
    :rtype: string

    """
    context = cast(Context, {"user": tk.g.user})
    if filter_type:
        action_functions = {
            "dataset": "package_activity_list",
            "user": "user_activity_list",
            "group": "group_activity_list",
            "organization": "organization_activity_list",
        }
        action_function = tk.get_action(action_functions[filter_type])
        return action_function(
            context, {
                "id": filter_id,
                "limit": limit,
                "offset": offset,
                "before": before,
                "after": after
                })
    else:
        return tk.get_action("dashboard_activity_list")(
            context, {
                "offset": offset,
                "limit": limit,
                "before": before,
                "after": after
                }
        )


def recently_changed_packages_activity_stream(
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    if limit:
        data_dict = {"limit": limit}
    else:
        data_dict = {}
    context = cast(
        Context, {"model": model, "session": model.Session, "user": tk.g.user}
    )
    return tk.get_action("recently_changed_packages_activity_list")(
        context, data_dict
    )


def new_activities() -> Optional[int]:
    """Return the number of activities for the current user.

    See :func:`logic.action.get.dashboard_new_activities_count` for more
    details.

    """
    if not tk.g.userobj:
        return None
    action = tk.get_action("dashboard_new_activities_count")
    return action({}, {})


def activity_list_select(
    pkg_activity_list: list[dict[str, Any]], current_activity_id: str
) -> list[Markup]:
    """
    Builds an HTML formatted list of options for the select lists
    on the "Changes" summary page.
    """
    select_list = []
    template = jinja2.Template(
        '<option value="{{activity_id}}" {{selected}}>{{timestamp}}</option>',
        autoescape=True,
    )
    for activity in pkg_activity_list:
        entry = tk.h.render_datetime(
            activity["timestamp"], with_hours=True, with_seconds=True
        )
        select_list.append(
            Markup(
                template.render(
                    activity_id=activity["id"],
                    timestamp=entry,
                    selected="selected"
                    if activity["id"] == current_activity_id
                    else "",
                )
            )
        )

    return select_list


def compare_pkg_dicts(
    old: dict[str, Any], new: dict[str, Any], old_activity_id: str
) -> list[dict[str, Any]]:
    """
    Takes two package dictionaries that represent consecutive versions of
    the same dataset and returns a list of detailed & formatted summaries of
    the changes between the two versions. old and new are the two package
    dictionaries. The function assumes that both dictionaries will have
    all of the default package dictionary keys, and also checks for fields
    added by extensions and extra fields added by the user in the web
    interface.

    Returns a list of dictionaries, each of which corresponds to a change
    to the dataset made in this revision. The dictionaries each contain a
    string indicating the type of change made as well as other data necessary
    to form a detailed summary of the change.
    """

    change_list: list[dict[str, Any]] = []

    changes.check_metadata_changes(change_list, old, new)

    changes.check_resource_changes(change_list, old, new, old_activity_id)

    # if the dataset was updated but none of the fields we check were changed,
    # display a message stating that
    if len(change_list) == 0:
        change_list.append({"type": "no_change"})

    return change_list


def compare_group_dicts(
    old: dict[str, Any], new: dict[str, Any], old_activity_id: str
):
    """
    Takes two package dictionaries that represent consecutive versions of
    the same organization and returns a list of detailed & formatted summaries
    of the changes between the two versions. old and new are the two package
    dictionaries. The function assumes that both dictionaries will have
    all of the default package dictionary keys, and also checks for fields
    added by extensions and extra fields added by the user in the web
    interface.

    Returns a list of dictionaries, each of which corresponds to a change
    to the dataset made in this revision. The dictionaries each contain a
    string indicating the type of change made as well as other data necessary
    to form a detailed summary of the change.
    """
    change_list: list[dict[str, Any]] = []

    changes.check_metadata_org_changes(change_list, old, new)

    # if the organization was updated but none of the fields we check
    # were changed, display a message stating that
    if len(change_list) == 0:
        change_list.append({"type": "no_change"})

    return change_list


def activity_show_email_notifications() -> bool:
    return tk.config.get("ckan.activity_streams_email_notifications")
