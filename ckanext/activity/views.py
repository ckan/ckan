# -*- coding: utf-8 -*-
from __future__ import annotations
import logging

import sqlalchemy as sa
from datetime import datetime
from typing import Any, Optional, Union, Tuple, List

from flask import Blueprint

import ckan.plugins.toolkit as tk
import ckan.model as model
from ckan.logic import NotFound
from ckan.views.group import (
    # TODO: don't use hidden funcitons
    _get_group_template,
)
from ckan.views.dataset import _get_pkg_template

from ckan.common import request as ckan_request

# TODO: don't use hidden funcitons
from ckan.views.user import _extra_template_variables

# TODO: don't use hidden funcitons
from ckan.views.dataset import _setup_template_variables
from ckan.views.admin import TrashView

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
    context: Context = {
        "auth_user_obj": tk.g.userobj,
        "for_view": True,
    }

    try:
        package = tk.get_action("package_show")(context, {"id": id})
    except (tk.ObjectNotFound, tk.NotAuthorized):
        return tk.abort(404, tk._("Dataset not found"))

    # view an 'old' version of the package, as recorded in the
    # activity stream
    current_pkg = package
    activity = context["session"].get(Activity, activity_id)
    if not activity:
        tk.abort(404, tk._("Dataset not found"))
    package = activity.data["package"]

    if package["id"] != current_pkg["id"]:
        log.info(
            "Mismatch between pkg id in activity and URL %s %s",
            package["id"], current_pkg["id"],
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

    try:
        resource_views = tk.get_action("resource_view_list")(
            context, {"id": resource["id"]}
        )
        resource["has_views"] = len(resource_views) > 0
    except NotFound:
        # Resource has been deleted since this version
        resource_views = []
        resource["has_views"] = False

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
    context: Context = {
        "for_view": True,
        "auth_user_obj": tk.g.userobj,
    }
    data_dict = {"id": id}

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
            "Attempt to view unmigrated or badly migrated dataset %s %s",
            id, activity_id,
        )
        tk.abort(
            404, tk._("The detail of this dataset activity is not available")
        )
    if pkg_dict["id"] != current_pkg["id"]:
        log.info(
            "Mismatch between pkg id in activity and URL %s %s",
            pkg_dict["id"], current_pkg["id"],
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
        try:
            resource_views = tk.get_action("resource_view_list")(
                context, {"id": resource["id"]}
            )
            resource["has_views"] = len(resource_views) > 0
        except NotFound:
            # Resource has been deleted since this version
            resource["has_views"] = False

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

    context: Context = {
        "for_view": True,
        "auth_user_obj": tk.g.userobj,
    }

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

    object_type = "package"
    blueprint = "activity.{}_activity".format(object_type)

    extra_vars = {
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
        "blueprint": blueprint,
        "object_type": object_type,
    }

    if ckan_request.htmx:
        return tk.render(
            "snippets/activity_stream.html", extra_vars
        )
    else:
        return tk.render(
            "package/activity_stream.html", extra_vars
        )


@bp.route("/dataset/changes/<id>")
def package_changes(id: str) -> Union[Response, str]:  # noqa
    """
    Shows the changes to a dataset in one particular activity stream item.
    """
    activity_id = id
    context: Context = {"auth_user_obj": tk.g.userobj}
    try:
        activity_diff = tk.get_action("activity_diff")(
            context,
            {"id": activity_id, "object_type": "package", "diff_type": "html"},
        )
    except tk.ObjectNotFound as e:
        log.info("Activity not found: %s - %s", e, activity_id)
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

    context: Context = {"auth_user_obj": tk.g.userobj}

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
            log.info("Activity not found: %s - %s", e, current_id)
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
    defaults={
        "group_type": "group",
        "is_organization": False,
    },
)
@bp.route(
    "/organization/activity/<id>",
    endpoint="organization_activity",
    defaults={
        "group_type": "organization",
        "is_organization": True,
    },
)
def group_activity(id: str, group_type: str, is_organization: bool) -> str:
    """Render this group's public activity stream page."""
    after = tk.request.args.get("after")
    before = tk.request.args.get("before")

    context: Context = {"user": tk.g.user, "for_view": True}

    try:
        action_name = "organization_show" if is_organization else "group_show"
        group_dict = tk.get_action(action_name)(context, {"id": id})
    except (tk.ObjectNotFound, tk.NotAuthorized):
        tk.abort(404, tk._("Group not found"))

    activity_type = tk.request.args.get("activity_type")
    activity_types = [activity_type] if activity_type else None

    limit = _get_activity_stream_limit()
    action_name = (
        "organization_activity_list"
        if is_organization
        else "group_activity_list"
    )
    try:
        activity_stream = tk.get_action(action_name)(
            context,
            {
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
    if is_organization:
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

    blueprint = "activity.{}_activity".format(group_type)

    extra_vars = {
        "id": id,
        "activity_stream": activity_stream,
        "group_type": group_dict["type"],
        "group_dict": group_dict,
        "activity_type": activity_type,
        "activity_types": filter_types.keys(),
        "newer_activities_url": newer_activities_url,
        "older_activities_url": older_activities_url,
        "blueprint": blueprint,
        "object_type": group_type,
    }

    if ckan_request.htmx:
        return tk.render(
            "snippets/activity_stream.html", extra_vars
        )
    else:
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
    activity_id = id
    context: Context = {
        "auth_user_obj": tk.g.userobj,
    }
    try:
        activity_diff = tk.get_action("activity_diff")(
            context,
            {"id": activity_id, "object_type": "group", "diff_type": "html"},
        )
    except tk.ObjectNotFound as e:
        log.info("Activity not found: %s - %s", e, activity_id)
        return tk.abort(404, tk._("Activity not found"))
    except tk.NotAuthorized:
        return tk.abort(403, tk._("Unauthorized to view activity data"))

    # 'group_dict' needs to go to the templates for page title & breadcrumbs.
    # Use the current version of the package, in case the name/title have
    # changed, and we need a link to it which works
    group_id = activity_diff["activities"][1]["data"]["group"]["id"]

    action_name = "organization_show" if is_organization else "group_show"
    current_group_dict = tk.get_action(action_name)(
        context, {"id": group_id}
    )
    action_name = (
        "organization_activity_list"
        if is_organization else "group_activity_list"
    )
    group_activity_list = tk.get_action(action_name)(
        context, {"id": group_id, "limit": 100}
    )

    extra_vars: dict[str, Any] = {
        "activity_diffs": [activity_diff],
        "group_dict": current_group_dict,
        "group_activity_list": group_activity_list,
        "group_type": current_group_dict["type"],
    }
    template_name = (
        "organization/changes.html"
        if is_organization else "group/changes.html"
    )
    return tk.render(template_name, extra_vars)


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
    new_id = tk.h.get_request_param("new_id")
    old_id = tk.h.get_request_param("old_id")

    context: Context = {
        "auth_user_obj": tk.g.userobj,
    }

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
            log.info("Activity not found: %s - %s", e, current_id)
            return tk.abort(404, tk._("Activity not found"))
        except tk.NotAuthorized:
            return tk.abort(403, tk._("Unauthorized to view activity data"))

        diff_list.append(activity_diff)

        if activity_diff["activities"][0]["id"] == old_id:
            done = True
        else:
            current_id = activity_diff["activities"][0]["id"]

    group_id: str = diff_list[0]["activities"][1]["data"]["group"]["id"]
    action_name = "organization_show" if is_organization else "group_show"
    current_group_dict = tk.get_action(action_name)(
        context, {"id": group_id}
    )
    action_name = (
        "organization_activity_list"
        if is_organization else "group_activity_list"
    )
    group_activity_list = tk.get_action(action_name)(
        context, {"id": group_id, "limit": 100}
    )

    extra_vars: dict[str, Any] = {
        "activity_diffs": diff_list,
        "group_dict": current_group_dict,
        "group_activity_list": group_activity_list,
        "group_type": current_group_dict["type"],
    }
    template_name = (
        "organization/changes.html"
        if is_organization else "group/changes.html"
    )
    return tk.render(template_name, extra_vars)


@bp.route("/user/activity/<id>")
def user_activity(id: str) -> str:
    """Render this user's public activity stream page."""
    after = tk.request.args.get("after")
    before = tk.request.args.get("before")

    context: Context = {
        "auth_user_obj": tk.g.userobj,
        "for_view": True,
    }
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

    if ckan_request.htmx:
        return tk.render(
            "snippets/activity_stream.html", extra_vars
        )
    else:
        return tk.render(
            "user/activity_stream.html", extra_vars
        )


@bp.route("/dashboard/", strict_slashes=False)
def dashboard() -> str:
    if tk.current_user.is_anonymous:
        tk.h.flash_error(tk._(u'Not authorized to see this page'))
        return tk.h.redirect_to(u'user.login')

    context: Context = {
        "auth_user_obj": tk.g.userobj,
        "for_view": True,
    }
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

    if ckan_request.htmx:
        return tk.render(
            "user/snippets/news_feed.html", extra_vars
        )
    else:
        return tk.render(
            "user/dashboard.html", extra_vars
        )


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
        context: Context = {
            "auth_user_obj": tk.g.userobj,
            "for_view": True,
        }
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


@bp.route("/testing/dashboard")
def dashboard_testing() -> str:
    return tk.render(
        'user/snippets/followee_dropdown.html', {
            'context': {},
            'followees': [
                {"dict": {"id": 1}, "display_name": "Test followee"},
                {"dict": {"id": 2}, "display_name": "Not valid"}
            ]
        }
    )


class ActivityTrashView(TrashView):
    def __init__(self):
        super(ActivityTrashView, self).__init__()
        self.deleted_activities = self._get_deleted_activities()

        # Include activities in the deleted_entities dictionary
        self.deleted_entities["activity"] = self.deleted_activities

        # Add messages for activities
        self.messages["confirm"]["activity"] = tk._(
            "Are you sure you want to purge activities?"
        )
        self.messages["success"]["activity"] = tk._(
            "{} activities have been purged"
        )
        self.messages["empty"]["activity"] = tk._(
            "There are no activities to purge"
        )

    # TODO
    def _get_deleted_activities(self) -> dict[str, list[Any]]:
        activities = (
            model.Session.query(Activity)
            .order_by(Activity.activity_type, sa.desc(Activity.timestamp))
            .all()
        )

        grouped_activities = {}
        for activity in activities:
            # Extract the date part from the timestamp
            date_str = activity.timestamp.strftime('%Y-%m-%d')

            # Initialize the list if the date is not already in the dict
            if date_str not in grouped_activities:
                grouped_activities[date_str] = []

            # Append the activity to the list for this date
            grouped_activities[date_str].append(activity)

        return grouped_activities

    def post(self) -> Response:
        if "cancel" in tk.request.form:
            return tk.h.redirect_to("admin.trash")

        req_action = tk.request.form.get("action", "")
        if req_action == "activity":
            self.purge_entity("activity")
            return tk.h.redirect_to("admin.trash")
        else:
            # Call the parent class's post method for other actions
            return super(ActivityTrashView, self).post()

    def _get_actions_and_entities(
        self,
    ) -> Tuple[Tuple[str, ...], Tuple[Union[List[Any], dict[str, list[Any]]], ...]]:
        actions, entities = super(
            ActivityTrashView, self
        )._get_actions_and_entities()

        actions += ("activity_purge",)
        entities += (self.deleted_activities,)
        return actions, entities

    @staticmethod
    def _get_purge_action(ent_type: str) -> str:
        if ent_type == "activity":
            return "activity_purge"
        return TrashView._get_purge_action(ent_type)


bp.add_url_rule(
    "/ckan-admin/trash", view_func=ActivityTrashView.as_view(str("trash"))
)
