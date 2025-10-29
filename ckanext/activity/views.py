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
from ckan.views.dataset import _get_pkg_template

# TODO: don't use hidden funcitons
from ckan.views.user import _extra_template_variables

# TODO: don't use hidden funcitons
from ckan.views.dataset import _setup_template_variables

from ckan.types import Context, Response
from .model import Activity
from .logic.validators import (
    VALIDATORS_PACKAGE_ACTIVITY_TYPES,
    VALIDATORS_GROUP_ACTIVITY_TYPES,
    VALIDATORS_ORGANIZATION_ACTIVITY_TYPES
)


log = logging.getLogger(__name__)
bp = Blueprint("activity", __name__)


def _get_activity_stream_limit() -> int:
    base_limit = tk.config.get("ckan.activity_list_limit")
    max_limit = tk.config.get("ckan.activity_list_limit_max")
    return min(base_limit, max_limit)


def _get_older_activities_url(
    has_more: bool,
    stream: list[dict[str, Any]],
    **kwargs: Any
) -> Any:
    """ Returns pagination's older activities url.

    If "after", we came from older activities, so we know it exists.
    if "before" (or is_first_page), we only show older activities if we know
    we have more rows
    """
    after = tk.request.args.get("after")
    before = tk.request.args.get("before")
    is_first_page = after is None and before is None
    url = None
    if after or (has_more and (before or is_first_page)):
        before_time = datetime.fromisoformat(
            stream[-1]["timestamp"]
        )
        url = tk.h.url_for(
            tk.request.endpoint,
            before=before_time.timestamp(),
            **kwargs
        )

    return url


def _get_newer_activities_url(
    has_more: bool,
    stream: list[dict[str, Any]],
    **kwargs: Any
) -> Any:
    """ Returns pagination's newer activities url.

    if "before", we came from the newer activities, so it exists.
    if "after", we only show newer activities if we know
    we have more rows
    """
    after = tk.request.args.get("after")
    before = tk.request.args.get("before")
    url = None

    if before or (has_more and after):
        after_time = datetime.fromisoformat(
            stream[0]["timestamp"]
        )
        url = tk.h.url_for(
            tk.request.endpoint,
            after=after_time.timestamp(),
            **kwargs
        )
    return url


@bp.route("/dataset/<id>/resources/<resource_id>/history/<activity_id>")
def resource_history(id: str, resource_id: str, activity_id: str) -> str:
    context = cast(
        Context,
        {
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
        "base_template": _get_pkg_template("resource_template", dataset_type),
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
            "base_template": _get_pkg_template("read_template", package_type),
            "dataset_type": package_type,
            "pkg_dict": pkg_dict,
            "pkg": pkg,
        },
    )


@bp.route("/dataset/activity/<id>")
def package_activity(id: str) -> Union[Response, str]:  # noqa
    """Render this package's public activity stream page."""
    after = tk.request.args.get("after")
    before = tk.request.args.get("before")
    activity_type = tk.request.args.get("activity_type")

    context = cast(
        Context,
        {
            "for_view": True,
            "auth_user_obj": tk.g.userobj,
        },
    )

    data_dict = {"id": id}
    limit = _get_activity_stream_limit()
    activity_types = [activity_type] if activity_type else None

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
        activity_stream = tk.get_action("package_activity_list")(
            context, activity_dict
        )
        dataset_type = pkg_dict["type"] or "dataset"
    except tk.ObjectNotFound:
        return tk.abort(404, tk._("Dataset not found"))
    except tk.NotAuthorized:
        return tk.abort(403, tk._("Unauthorized to read dataset %s") % id)
    except tk.ValidationError:
        return tk.abort(400, tk._("Invalid parameters"))

    has_more = len(activity_stream) > limit
    # remove the extra item if exists
    if has_more:
        if after:
            activity_stream.pop(0)
        else:
            activity_stream.pop()

    older_activities_url = _get_older_activities_url(
        has_more,
        activity_stream,
        id=id,
        activity_type=activity_type
        )

    newer_activities_url = _get_newer_activities_url(
        has_more,
        activity_stream,
        id=id,
        activity_type=activity_type
    )

    return tk.render(
        "package/activity_stream.html",
        {
            "dataset_type": dataset_type,
            "pkg_dict": pkg_dict,
            "activity_stream": activity_stream,
            "id": id,  # i.e. package's current name
            "limit": limit,
            "has_more": has_more,
            "activity_type": activity_type,
            "activity_types": VALIDATORS_PACKAGE_ACTIVITY_TYPES.keys(),
            "newer_activities_url": newer_activities_url,
            "older_activities_url": older_activities_url,
        },
    )


@bp.route("/dataset/changes/<id>")
def package_changes(id: str) -> Union[Response, str]:  # noqa
    """
    Shows the changes to a dataset in one particular activity stream item.
    """
    activity_id = id
    context = cast(Context, {"auth_user_obj": tk.g.userobj})
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

    context = cast(Context, {"auth_user_obj": tk.g.userobj})

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
    if time_diff.total_seconds() <= 0:
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
    "/group/activity/<id>",
    endpoint="group_activity",
    defaults={"group_type": "group"},
)
@bp.route(
    "/organization/activity/<id>",
    endpoint="organization_activity",
    defaults={"group_type": "organization"},
)
def group_activity(id: str, group_type: str) -> str:
    """Render this group's public activity stream page."""
    after = tk.request.args.get("after")
    before = tk.request.args.get("before")

    if group_type == 'organization':
        set_org(True)

    context = cast(Context, {"user": tk.g.user, "for_view": True})

    try:
        group_dict = _get_group_dict(id, group_type)
    except (tk.ObjectNotFound, tk.NotAuthorized):
        tk.abort(404, tk._("Group not found"))

    real_group_type = group_dict["type"]
    action_name = "organization_activity_list"
    if not group_dict.get("is_organization"):
        action_name = "group_activity_list"

    activity_type = tk.request.args.get("activity_type")
    activity_types = [activity_type] if activity_type else None

    limit = _get_activity_stream_limit()

    try:
        activity_stream = tk.get_action(action_name)(
            context, {
                "id": group_dict["id"],
                "before": before,
                "after": after,
                "limit": limit + 1,
                "activity_types": activity_types
                }
            )
    except tk.ValidationError as error:
        tk.abort(400, error.message or "")

    filter_types = VALIDATORS_PACKAGE_ACTIVITY_TYPES.copy()
    if group_type == 'organization':
        filter_types.update(VALIDATORS_ORGANIZATION_ACTIVITY_TYPES)
    else:
        filter_types.update(VALIDATORS_GROUP_ACTIVITY_TYPES)

    has_more = len(activity_stream) > limit
    # remove the extra item if exists
    if has_more:
        if after:
            activity_stream.pop(0)
        else:
            activity_stream.pop()

    older_activities_url = _get_older_activities_url(
        has_more,
        activity_stream,
        id=id,
        activity_type=activity_type
    )

    newer_activities_url = _get_newer_activities_url(
        has_more,
        activity_stream,
        id=id,
        activity_type=activity_type
    )

    extra_vars = {
        "id": id,
        "activity_stream": activity_stream,
        "group_type": real_group_type,
        "group_dict": group_dict,
        "activity_type": activity_type,
        "activity_types": filter_types.keys(),
        "newer_activities_url": newer_activities_url,
        "older_activities_url": older_activities_url
    }

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
    extra_vars = {}
    activity_id = id
    context = cast(
        Context,
        {
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
    extra_vars = {}
    new_id = tk.h.get_request_param("new_id")
    old_id = tk.h.get_request_param("old_id")

    context = cast(
        Context,
        {
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
def user_activity(id: str) -> str:
    """Render this user's public activity stream page."""
    after = tk.request.args.get("after")
    before = tk.request.args.get("before")

    context = cast(
        Context,
        {
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

    limit = _get_activity_stream_limit()

    try:
        activity_stream = tk.get_action(
            "user_activity_list"
        )(context, {
            "id": extra_vars["user_dict"]["id"],
            "before": before,
            "after": after,
            "limit": limit + 1,
        })
    except tk.ValidationError:
        tk.abort(400)

    has_more = len(activity_stream) > limit
    # remove the extra item if exists
    if has_more:
        if after:
            activity_stream.pop(0)
        else:
            activity_stream.pop()

    older_activities_url = _get_older_activities_url(
        has_more,
        activity_stream,
        id=id
    )

    newer_activities_url = _get_newer_activities_url(
        has_more,
        activity_stream,
        id=id
    )

    extra_vars.update({
        "id":  id,
        "activity_stream": activity_stream,
        "newer_activities_url": newer_activities_url,
        "older_activities_url": older_activities_url
    })

    return tk.render("user/activity_stream.html", extra_vars)


@bp.route("/dashboard/", strict_slashes=False)
def dashboard() -> str:
    context = cast(
        Context,
        {
            "auth_user_obj": tk.g.userobj,
            "for_view": True,
        },
    )
    data_dict: dict[str, Any] = {"user_obj": tk.g.userobj}
    extra_vars = _extra_template_variables(context, data_dict)

    q = tk.request.args.get("q", "")
    filter_type = tk.request.args.get("type", "")
    filter_id = tk.request.args.get("name", "")
    before = tk.request.args.get("before")
    after = tk.request.args.get("after")

    limit = _get_activity_stream_limit()

    extra_vars["followee_list"] = tk.get_action("followee_list")(
        context, {"id": tk.g.userobj.id, "q": q}
    )
    extra_vars["dashboard_activity_stream_context"] = _get_dashboard_context(
        filter_type, filter_id, q
    )
    activity_stream = tk.h.dashboard_activity_stream(
        tk.g.userobj.id,
        filter_type=filter_type,
        filter_id=filter_id,
        limit=limit + 1,
        before=before,
        after=after
    )

    has_more = len(activity_stream) > limit
    # remove the extra item if exists
    if has_more:
        if after:
            activity_stream.pop(0)
        else:
            activity_stream.pop()

    older_activities_url = _get_older_activities_url(
        has_more,
        activity_stream,
        type=filter_type,
        name=filter_id
    )

    newer_activities_url = _get_newer_activities_url(
        has_more,
        activity_stream,
        type=filter_type,
        name=filter_id
    )

    extra_vars.update({
        "id":  id,
        "dashboard_activity_stream": activity_stream,
        "newer_activities_url": newer_activities_url,
        "older_activities_url": older_activities_url
    })

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
