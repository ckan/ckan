# -*- coding: utf-8 -*-
from __future__ import annotations
import logging

from datetime import datetime
from typing import Any, Optional, Union, cast

from flask import Blueprint

import ckan.plugins.toolkit as tk
import ckan.model as model
from ckan.views.group import (
    set_org,
    # TODO: don't use hidden funcitons
    _get_group_dict,
    _get_group_template,
    _replace_group_org,
)

# TODO: don't use hidden funcitons
from ckan.views.user import _extra_template_variables

# TODO: don't use hidden funcitons
from ckan.views.dataset import _setup_template_variables

from ckan.types import Context, Response
from .model import Activity
from .logic.validators import VALIDATORS_PACKAGE_ACTIVITY_TYPES


log = logging.getLogger(__name__)
bp = Blueprint("activity", __name__)


@bp.route("/dataset/<id>/resources/<resource_id>/history/<activity_id>")
def resource_history(id: str, resource_id: str, activity_id: str) -> str:
    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "auth_user_obj": tk.g.userobj,
            "for_view": True,
        },
    )

    try:
        package = tk.get_action("package_show")(context, {"id": id})
    except (tk.ObjectNotFound, tk.NotAuthorized):
        return tk.abort(404, tk._("Dataset not found"))

    # view an 'old' version of the package, as recorded in the
    # activity stream
    current_pkg = package
    try:
        activity = context["session"].query(Activity).get(activity_id)
        assert activity
        package = activity.data["package"]
    except AttributeError:
        tk.abort(404, tk._("Dataset not found"))

    if package["id"] != current_pkg["id"]:
        log.info(
            "Mismatch between pkg id in activity and URL {} {}".format(
                package["id"], current_pkg["id"]
            )
        )
        # the activity is not for the package in the URL - don't allow
        # misleading URLs as could be malicious
        tk.abort(404, tk._("Activity not found"))
    # The name is used lots in the template for links, so fix it to be
    # the current one. It's not displayed to the user anyway.
    package["name"] = current_pkg["name"]

    # Don't crash on old (unmigrated) activity records, which do not
    # include resources or extras.
    package.setdefault("resources", [])

    resource = None
    for res in package.get("resources", []):
        if res["id"] == resource_id:
            resource = res
            break
    if not resource:
        return tk.abort(404, tk._("Resource not found"))

    # get package license info
    license_id = package.get("license_id")
    try:
        package["isopen"] = model.Package.get_license_register()[
            license_id
        ].isopen()
    except KeyError:
        package["isopen"] = False

    resource_views = tk.get_action("resource_view_list")(
        context, {"id": resource_id}
    )
    resource["has_views"] = len(resource_views) > 0

    current_resource_view = None
    view_id = tk.request.args.get("view_id")
    if resource["has_views"]:
        if view_id:
            current_resource_view = [
                rv for rv in resource_views if rv["id"] == view_id
            ]
            if len(current_resource_view) == 1:
                current_resource_view = current_resource_view[0]
            else:
                return tk.abort(404, tk._("Resource view not found"))
        else:
            current_resource_view = resource_views[0]

    # required for nav menu
    pkg = context["package"]
    dataset_type = pkg.type

    # TODO: remove
    tk.g.package = package
    tk.g.resource = resource
    tk.g.pkg = pkg
    tk.g.pkg_dict = package

    extra_vars: dict[str, Any] = {
        "resource_views": resource_views,
        "current_resource_view": current_resource_view,
        "dataset_type": dataset_type,
        "pkg_dict": package,
        "package": package,
        "resource": resource,
        "pkg": pkg,  # NB it is the current version of the dataset, so ignores
        # activity_id. Still used though in resource views for
        # backward compatibility
    }

    return tk.render("package/resource_history.html", extra_vars)


@bp.route("/dataset/<id>/history/<activity_id>")
def package_history(id: str, activity_id: str) -> Union[Response, str]:
    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "for_view": True,
            "auth_user_obj": tk.g.userobj,
        },
    )
    data_dict = {"id": id, "include_tracking": True}

    # check if package exists
    try:
        pkg_dict = tk.get_action("package_show")(context, data_dict)
        pkg = context["package"]
    except (tk.ObjectNotFound, tk.NotAuthorized):
        return tk.abort(404, tk._("Dataset not found"))

    # if the user specified a package id, redirect to the package name
    if (
        data_dict["id"] == pkg_dict["id"]
        and data_dict["id"] != pkg_dict["name"]
    ):
        return tk.h.redirect_to(
            "activity.package_history",
            id=pkg_dict["name"],
            activity_id=activity_id,
        )

    tk.g.pkg_dict = pkg_dict
    tk.g.pkg = pkg
    # NB templates should not use g.pkg, because it takes no account of
    # activity_id

    # view an 'old' version of the package, as recorded in the
    # activity stream
    try:
        activity = tk.get_action("activity_show")(
            context, {"id": activity_id, "include_data": True}
        )
    except tk.ObjectNotFound:
        tk.abort(404, tk._("Activity not found"))
    except tk.NotAuthorized:
        tk.abort(403, tk._("Unauthorized to view activity data"))
    current_pkg = pkg_dict
    try:
        pkg_dict = activity["data"]["package"]
    except KeyError:
        tk.abort(404, tk._("Dataset not found"))
    if "id" not in pkg_dict or "resources" not in pkg_dict:
        log.info(
            "Attempt to view unmigrated or badly migrated dataset "
            "{} {}".format(id, activity_id)
        )
        tk.abort(
            404, tk._("The detail of this dataset activity is not available")
        )
    if pkg_dict["id"] != current_pkg["id"]:
        log.info(
            "Mismatch between pkg id in activity and URL {} {}".format(
                pkg_dict["id"], current_pkg["id"]
            )
        )
        # the activity is not for the package in the URL - don't allow
        # misleading URLs as could be malicious
        tk.abort(404, tk._("Activity not found"))
    # The name is used lots in the template for links, so fix it to be
    # the current one. It's not displayed to the user anyway.
    pkg_dict["name"] = current_pkg["name"]

    # Earlier versions of CKAN only stored the package table in the
    # activity, so add a placeholder for resources, or the template
    # will crash.
    pkg_dict.setdefault("resources", [])

    # can the resources be previewed?
    for resource in pkg_dict["resources"]:
        resource_views = tk.get_action("resource_view_list")(
            context, {"id": resource["id"]}
        )
        resource["has_views"] = len(resource_views) > 0

    package_type = pkg_dict["type"] or "dataset"
    _setup_template_variables(context, {"id": id}, package_type=package_type)

    return tk.render(
        "package/history.html",
        {
            "dataset_type": package_type,
            "pkg_dict": pkg_dict,
            "pkg": pkg,
        },
    )


@bp.route("/dataset/activity/<id>")
def package_activity(id: str) -> Union[Response, str]:  # noqa
    """Render this package's public activity stream page."""
    after = tk.h.get_request_param("after")
    before = tk.h.get_request_param("before")
    activity_type = tk.h.get_request_param("activity_type")

    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "for_view": True,
            "auth_user_obj": tk.g.userobj,
        },
    )

    data_dict = {"id": id}
    base_limit = tk.config.get_value("ckan.activity_list_limit")
    max_limit = tk.config.get_value("ckan.activity_list_limit_max")
    limit = min(base_limit, max_limit)
    activity_types = [activity_type] if activity_type else None
    is_first_page = after is None and before is None

    try:
        pkg_dict = tk.get_action("package_show")(context, data_dict)
        activity_dict = {
            "id": pkg_dict["id"],
            "after": after,
            "before": before,
            # ask for one more just to know if this query has more results
            "limit": limit + 1,
            "activity_types": activity_types,
        }
        pkg = context["package"]
        package_activity_stream = tk.get_action("package_activity_list")(
            context, activity_dict
        )
        dataset_type = pkg_dict["type"] or "dataset"
    except tk.ObjectNotFound:
        return tk.abort(404, tk._("Dataset not found"))
    except tk.NotAuthorized:
        return tk.abort(403, tk._("Unauthorized to read dataset %s") % id)
    except tk.ValidationError:
        return tk.abort(400, tk._("Invalid parameters"))

    prev_page = None
    next_page = None

    has_more = len(package_activity_stream) > limit
    # remove the extra item if exists
    if has_more:
        if after:
            # drop the first element
            package_activity_stream.pop(0)
        else:
            # drop the last element
            package_activity_stream.pop()

    # if "after", we came from the next page. So it exists
    # if "before" (or is_first_page), we only show next page if we know
    # we have more rows
    if after or (has_more and (before or is_first_page)):
        before_time = datetime.fromisoformat(
            package_activity_stream[-1]["timestamp"]
        )
        next_page = tk.h.url_for(
            "dataset.activity",
            id=id,
            activity_type=activity_type,
            before=before_time.timestamp(),
        )

    # if "before", we came from the previous page. So it exists
    # if "after", we only show previous page if we know
    # we have more rows
    if before or (has_more and after):
        after_time = datetime.fromisoformat(
            package_activity_stream[0]["timestamp"]
        )
        prev_page = tk.h.url_for(
            "dataset.activity",
            id=id,
            activity_type=activity_type,
            after=after_time.timestamp(),
        )

    return tk.render(
        "package/activity.html",
        {
            "dataset_type": dataset_type,
            "pkg_dict": pkg_dict,
            "pkg": pkg,
            "activity_stream": package_activity_stream,
            "id": id,  # i.e. package's current name
            "limit": limit,
            "has_more": has_more,
            "activity_type": activity_type,
            "activity_types": VALIDATORS_PACKAGE_ACTIVITY_TYPES.keys(),
            "prev_page": prev_page,
            "next_page": next_page,
        },
    )


@bp.route("/dataset/changes/<id>")
def package_changes(id: str) -> Union[Response, str]:  # noqa
    """
    Shows the changes to a dataset in one particular activity stream item.
    """
    activity_id = id
    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "auth_user_obj": tk.g.userobj,
        },
    )
    try:
        activity_diff = tk.get_action("activity_diff")(
            context,
            {"id": activity_id, "object_type": "package", "diff_type": "html"},
        )
    except tk.ObjectNotFound as e:
        log.info("Activity not found: {} - {}".format(str(e), activity_id))
        return tk.abort(404, tk._("Activity not found"))
    except tk.NotAuthorized:
        return tk.abort(403, tk._("Unauthorized to view activity data"))

    # 'pkg_dict' needs to go to the templates for page title & breadcrumbs.
    # Use the current version of the package, in case the name/title have
    # changed, and we need a link to it which works
    pkg_id = activity_diff["activities"][1]["data"]["package"]["id"]
    current_pkg_dict = tk.get_action("package_show")(context, {"id": pkg_id})
    pkg_activity_list = tk.get_action("package_activity_list")(
        context, {"id": pkg_id, "limit": 100}
    )

    return tk.render(
        "package/changes.html",
        {
            "activity_diffs": [activity_diff],
            "pkg_dict": current_pkg_dict,
            "pkg_activity_list": pkg_activity_list,
            "dataset_type": current_pkg_dict["type"],
        },
    )


@bp.route("/dataset/changes_multiple")
def package_changes_multiple() -> Union[Response, str]:  # noqa
    """
    Called when a user specifies a range of versions they want to look at
    changes between. Verifies that the range is valid and finds the set of
    activity diffs for the changes in the given version range, then
    re-renders changes.html with the list.
    """

    new_id = tk.h.get_request_param("new_id")
    old_id = tk.h.get_request_param("old_id")

    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "auth_user_obj": tk.g.userobj,
        },
    )

    # check to ensure that the old activity is actually older than
    # the new activity
    old_activity = tk.get_action("activity_show")(
        context, {"id": old_id, "include_data": False}
    )
    new_activity = tk.get_action("activity_show")(
        context, {"id": new_id, "include_data": False}
    )

    old_timestamp = old_activity["timestamp"]
    new_timestamp = new_activity["timestamp"]

    t1 = datetime.strptime(old_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
    t2 = datetime.strptime(new_timestamp, "%Y-%m-%dT%H:%M:%S.%f")

    time_diff = t2 - t1
    # if the time difference is negative, just return the change that put us
    # at the more recent ID we were just looking at
    # TODO: do something better here - go back to the previous page,
    # display a warning that the user can't look at a sequence where
    # the newest item is older than the oldest one, etc
    if time_diff.total_seconds() < 0:
        return package_changes(tk.h.get_request_param("current_new_id"))

    done = False
    current_id = new_id
    diff_list = []

    while not done:
        try:
            activity_diff = tk.get_action("activity_diff")(
                context,
                {
                    "id": current_id,
                    "object_type": "package",
                    "diff_type": "html",
                },
            )
        except tk.ObjectNotFound as e:
            log.info("Activity not found: {} - {}".format(str(e), current_id))
            return tk.abort(404, tk._("Activity not found"))
        except tk.NotAuthorized:
            return tk.abort(403, tk._("Unauthorized to view activity data"))

        diff_list.append(activity_diff)

        if activity_diff["activities"][0]["id"] == old_id:
            done = True
        else:
            current_id = activity_diff["activities"][0]["id"]

    pkg_id: str = diff_list[0]["activities"][1]["data"]["package"]["id"]
    current_pkg_dict = tk.get_action("package_show")(context, {"id": pkg_id})
    pkg_activity_list = tk.get_action("package_activity_list")(
        context, {"id": pkg_id, "limit": 100}
    )

    return tk.render(
        "package/changes.html",
        {
            "activity_diffs": diff_list,
            "pkg_dict": current_pkg_dict,
            "pkg_activity_list": pkg_activity_list,
            "dataset_type": current_pkg_dict["type"],
        },
    )


@bp.route(
    "/group/activity/<id>/<int:offset>",
    endpoint="group_activity",
    defaults={"is_organization": False, "group_type": "group", "offset": 0},
)
@bp.route(
    "/organization/activity/<id>/<int:offset>",
    endpoint="organization_activity",
    defaults={
        "is_organization": True,
        "group_type": "organization",
        "offset": 0,
    },
)
def group_activity(
    id: str, group_type: str, is_organization: bool, offset: int = 0
) -> str:
    """Render this group's public activity stream page."""
    extra_vars = {}
    set_org(is_organization)
    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "for_view": True,
        },
    )
    try:
        group_dict = _get_group_dict(id, group_type)
    except (tk.ObjectNotFound, tk.NotAuthorized):
        tk.abort(404, tk._("Group not found"))

    try:
        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html
        # template to retrieve later.
        extra_vars["activity_stream"] = tk.get_action(
            "organization_activity_list"
            if group_dict.get("is_organization")
            else "group_activity_list"
        )(context, {"id": group_dict["id"], "offset": offset})

    except tk.ValidationError as error:
        tk.abort(400, error.message or "")

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    tk.g.group_activity_stream = extra_vars["activity_stream"]
    tk.g.group_dict = group_dict

    extra_vars["group_type"] = group_type
    extra_vars["group_dict"] = group_dict
    extra_vars["id"] = id
    return tk.render(
        _get_group_template("activity_template", group_type), extra_vars
    )


@bp.route(
    "/group/changes/<id>",
    defaults={"is_organization": False, "group_type": "group"},
)
@bp.route(
    "/organization/changes/<id>",
    endpoint="organization_changes",
    defaults={"is_organization": True, "group_type": "organization"},
)
def group_changes(id: str, group_type: str, is_organization: bool) -> str:
    """
    Shows the changes to an organization in one particular activity stream
    item.
    """
    set_org(is_organization)
    extra_vars = {}
    activity_id = id
    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "auth_user_obj": tk.g.userobj,
        },
    )
    try:
        activity_diff = tk.get_action("activity_diff")(
            context,
            {"id": activity_id, "object_type": "group", "diff_type": "html"},
        )
    except tk.ObjectNotFound as e:
        log.info("Activity not found: {} - {}".format(str(e), activity_id))
        return tk.abort(404, tk._("Activity not found"))
    except tk.NotAuthorized:
        return tk.abort(403, tk._("Unauthorized to view activity data"))

    # 'group_dict' needs to go to the templates for page title & breadcrumbs.
    # Use the current version of the package, in case the name/title have
    # changed, and we need a link to it which works
    group_id = activity_diff["activities"][1]["data"]["group"]["id"]
    current_group_dict = tk.get_action(group_type + "_show")(
        context, {"id": group_id}
    )
    group_activity_list = tk.get_action(group_type + "_activity_list")(
        context, {"id": group_id, "limit": 100}
    )

    extra_vars: dict[str, Any] = {
        "activity_diffs": [activity_diff],
        "group_dict": current_group_dict,
        "group_activity_list": group_activity_list,
        "group_type": current_group_dict["type"],
    }

    return tk.render(_replace_group_org("group/changes.html"), extra_vars)


@bp.route(
    "/group/changes_multiple",
    defaults={"is_organization": False, "group_type": "group"},
)
@bp.route(
    "/organization/changes_multiple",
    endpoint="organization_changes_multiple",
    defaults={"is_organization": True, "group_type": "organization"},
)
def group_changes_multiple(is_organization: bool, group_type: str) -> str:
    """
    Called when a user specifies a range of versions they want to look at
    changes between. Verifies that the range is valid and finds the set of
    activity diffs for the changes in the given version range, then
    re-renders changes.html with the list.
    """
    set_org(is_organization)
    extra_vars = {}
    new_id = tk.h.get_request_param("new_id")
    old_id = tk.h.get_request_param("old_id")

    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "auth_user_obj": tk.g.userobj,
        },
    )

    # check to ensure that the old activity is actually older than
    # the new activity
    old_activity = tk.get_action("activity_show")(
        context, {"id": old_id, "include_data": False}
    )
    new_activity = tk.get_action("activity_show")(
        context, {"id": new_id, "include_data": False}
    )

    old_timestamp = old_activity["timestamp"]
    new_timestamp = new_activity["timestamp"]

    t1 = datetime.strptime(old_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
    t2 = datetime.strptime(new_timestamp, "%Y-%m-%dT%H:%M:%S.%f")

    time_diff = t2 - t1
    # if the time difference is negative, just return the change that put us
    # at the more recent ID we were just looking at
    # TODO: do something better here - go back to the previous page,
    # display a warning that the user can't look at a sequence where
    # the newest item is older than the oldest one, etc
    if time_diff.total_seconds() < 0:
        return group_changes(
            tk.h.get_request_param("current_new_id"),
            group_type,
            is_organization,
        )

    done = False
    current_id = new_id
    diff_list = []

    while not done:
        try:
            activity_diff = tk.get_action("activity_diff")(
                context,
                {
                    "id": current_id,
                    "object_type": "group",
                    "diff_type": "html",
                },
            )
        except tk.ObjectNotFound as e:
            log.info("Activity not found: {} - {}".format(str(e), current_id))
            return tk.abort(404, tk._("Activity not found"))
        except tk.NotAuthorized:
            return tk.abort(403, tk._("Unauthorized to view activity data"))

        diff_list.append(activity_diff)

        if activity_diff["activities"][0]["id"] == old_id:
            done = True
        else:
            current_id = activity_diff["activities"][0]["id"]

    group_id: str = diff_list[0]["activities"][1]["data"]["group"]["id"]
    current_group_dict = tk.get_action(group_type + "_show")(
        context, {"id": group_id}
    )
    group_activity_list = tk.get_action(group_type + "_activity_list")(
        context, {"id": group_id, "limit": 100}
    )

    extra_vars: dict[str, Any] = {
        "activity_diffs": diff_list,
        "group_dict": current_group_dict,
        "group_activity_list": group_activity_list,
        "group_type": current_group_dict["type"],
    }

    return tk.render(_replace_group_org("group/changes.html"), extra_vars)


@bp.route("/user/activity/<id>")
@bp.route("/user/activity/<id>/<int:offset>")
def user_activity(id: str, offset: int = 0) -> str:
    """Render this user's public activity stream page."""
    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "auth_user_obj": tk.g.userobj,
            "for_view": True,
        },
    )
    data_dict: dict[str, Any] = {
        "id": id,
        "user_obj": tk.g.userobj,
        "include_num_followers": True,
    }
    try:
        tk.check_access("user_show", context, data_dict)
    except tk.NotAuthorized:
        tk.abort(403, tk._("Not authorized to see this page"))

    extra_vars = _extra_template_variables(context, data_dict)

    try:
        extra_vars["user_activity_stream"] = tk.get_action(
            "user_activity_list"
        )(context, {"id": extra_vars["user_dict"]["id"], "offset": offset})
    except tk.ValidationError:
        tk.abort(400)
    extra_vars["id"] = id

    return tk.render("user/activity_stream.html", extra_vars)


@bp.route("/dashboard/", strict_slashes=False, defaults={"offset": 0})
@bp.route("/dashboard/<int:offset>")
def dashboard(offset: int = 0) -> str:
    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": tk.g.user,
            "auth_user_obj": tk.g.userobj,
            "for_view": True,
        },
    )
    data_dict: dict[str, Any] = {"user_obj": tk.g.userobj, "offset": offset}
    extra_vars = _extra_template_variables(context, data_dict)

    q = tk.request.args.get("q", "")
    filter_type = tk.request.args.get("type", "")
    filter_id = tk.request.args.get("name", "")

    extra_vars["followee_list"] = tk.get_action("followee_list")(
        context, {"id": tk.g.userobj.id, "q": q}
    )
    extra_vars["dashboard_activity_stream_context"] = _get_dashboard_context(
        filter_type, filter_id, q
    )
    extra_vars["dashboard_activity_stream"] = tk.h.dashboard_activity_stream(
        tk.g.userobj.id, filter_type, filter_id, offset
    )

    # Mark the user's new activities as old whenever they view their
    # dashboard page.
    tk.get_action("dashboard_mark_activities_old")(context, {})

    return tk.render("user/dashboard.html", extra_vars)


def _get_dashboard_context(
    filter_type: Optional[str] = None,
    filter_id: Optional[str] = None,
    q: Optional[str] = None,
) -> dict[str, Any]:
    """Return a dict needed by the dashboard view to determine context."""

    def display_name(followee: dict[str, Any]) -> Optional[str]:
        """Return a display name for a user, group or dataset dict."""
        display_name = followee.get("display_name")
        fullname = followee.get("fullname")
        title = followee.get("title")
        name = followee.get("name")
        return display_name or fullname or title or name

    if filter_type and filter_id:
        context = cast(
            Context,
            {
                "model": model,
                "session": model.Session,
                "user": tk.g.user,
                "auth_user_obj": tk.g.userobj,
                "for_view": True,
            },
        )
        data_dict: dict[str, Any] = {
            "id": filter_id,
            "include_num_followers": True,
        }
        followee = None

        action_functions = {
            "dataset": "package_show",
            "user": "user_show",
            "group": "group_show",
            "organization": "organization_show",
        }
        action_name = action_functions.get(filter_type)
        if action_name is None:
            tk.abort(404, tk._("Follow item not found"))

        action_function = tk.get_action(action_name)
        try:
            followee = action_function(context, data_dict)
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._("{0} not found").format(filter_type))

        if followee is not None:
            return {
                "filter_type": filter_type,
                "q": q,
                "context": display_name(followee),
                "selected_id": followee.get("id"),
                "dict": followee,
            }

    return {
        "filter_type": filter_type,
        "q": q,
        "context": tk._("Everything"),
        "selected_id": False,
        "dict": None,
    }
