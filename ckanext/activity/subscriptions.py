# -*- coding: utf-8 -*-

from __future__ import annotations
import logging
from typing import Any
from typing_extensions import Literal

import ckan.plugins.toolkit as tk
import ckan.lib.dictization as dictization

from ckan import types, model
from ckan.lib.plugins import get_permission_labels
from .model import Activity

log = logging.getLogger(__name__)


def get_subscriptions() -> types.SignalMapping:
    return {
        tk.signals.action_succeeded: [
            {"sender": "bulk_update_public", "receiver": bulk_changed},
            {"sender": "bulk_update_private", "receiver": bulk_changed},
            {"sender": "bulk_update_delete", "receiver": bulk_changed},
            {"sender": "package_create", "receiver": package_changed},
            {"sender": "package_update", "receiver": package_changed},
            {"sender": "package_delete", "receiver": package_changed},
            {
                "sender": "resource_view_create",
                "receiver": resource_view_changed,
            },
            {
                "sender": "resource_view_delete",
                "receiver": resource_view_changed,
            },
            {
                "sender": "resource_view_update",
                "receiver": resource_view_changed,
            },
            {"sender": "group_create", "receiver": group_or_org_changed},
            {"sender": "group_update", "receiver": group_or_org_changed},
            {"sender": "group_delete", "receiver": group_or_org_changed},
            {
                "sender": "organization_create",
                "receiver": group_or_org_changed,
            },
            {
                "sender": "organization_update",
                "receiver": group_or_org_changed,
            },
            {
                "sender": "organization_delete",
                "receiver": group_or_org_changed,
            },
            {"sender": "user_create", "receiver": user_changed},
            {"sender": "user_update", "receiver": user_changed},
        ]
    }


# action, context, data_dict, result
def bulk_changed(sender: str, **kwargs: Any):
    for key in ("context", "data_dict"):
        if key not in kwargs:
            log.warning("Activity subscription ignored")
            return

    datasets = kwargs["data_dict"].get("datasets", [])

    for dataset in datasets:
        _create_package_activity(
            "changed",
            dataset,
            tk.fresh_context(kwargs["context"])
        )


def _create_package_activity(
        activity_type: Literal["new", "changed", "deleted"],
        pkg_id_or_name: str,
        context: types.Context,
):
    user_obj = _get_user_or_raise(context["user"])
    user_id = user_obj.id

    pkg = model.Package.get(pkg_id_or_name)
    if not pkg:
        raise tk.ObjectNotFound("package")

    # Handle 'deleted' objects.
    # When the user marks a package as deleted this comes through here as
    # a 'changed' package activity. We detect this and change it to a
    # 'deleted' activity.
    if activity_type == "changed" and pkg.state == "deleted":
        q = context["session"].query(Activity).filter_by(
            object_id=pkg.id, activity_type="deleted"
        ).exists()
        if context["session"].query(q).scalar():
            # A 'deleted' activity for this object has already been emitted
            # FIXME: What if the object was deleted and then activated
            # again?
            return None
        # Emit a 'deleted' activity for this object.
        activity_type = "deleted"

    try:
        # We save the entire rendered package dict so we can support
        # viewing the past packages from the activity feed.
        dictized_package = tk.get_action("package_show")(
            {
                # avoid ckanext-multilingual translating it
                "for_view": False,
                "ignore_auth": True,
            },
            {"id": pkg.id, "include_tracking": False},
        )
    except tk.ObjectNotFound:
        # This happens if this package is being purged and therefore has no
        # current revision.
        # TODO: Purge all related activity stream items when a model object
        # is purged.
        return None

    context["ignore_auth"] = True

    activity_dict = {
        "user_id": user_id,
        "object_id": pkg.id,
        "activity_type": f"{activity_type} package",
        "data": {
            "package": dictized_package,
            "actor": user_obj.name if user_obj else None,
        },
        "permission_labels": get_permission_labels().get_dataset_labels(pkg),
    }

    tk.get_action("activity_create")(context, activity_dict)


def _get_user_or_raise(username: str) -> model.User:
    """Get user by username or raise standard exception.
    """
    if user := model.User.get(username):
        return user

    raise tk.ValidationError({
        "user_id": ["User not found"]
    })


# action, context, data_dict, result
def package_changed(sender: str, **kwargs: Any):
    for key in ("result", "context", "data_dict"):
        if key not in kwargs:
            log.warning("Activity subscription ignored")
            return

    result: types.ActionResult.PackageUpdate = kwargs["result"]
    data_dict = kwargs["data_dict"]

    if not result:
        id_ = data_dict["id"]
    elif isinstance(result, str):
        id_ = result
    else:
        id_ = result["id"]

    _create_package_activity(
        "new" if sender == "package_create" else "changed",
        id_,
        tk.fresh_context(kwargs["context"])
    )


# action, context, data_dict, result
def resource_view_changed(sender: str, **kwargs: Any):
    for key in ("result", "context", "data_dict"):
        if key not in kwargs:
            log.warning("Activity subscription ignored")
            return

    context: types.Context = kwargs["context"]
    result: types.ActionResult.ResourceViewUpdate = kwargs["result"]
    data_dict = kwargs["data_dict"]

    if context.get("preview"):
        return

    if not result:
        id_ = data_dict["id"]
    elif isinstance(result, str):
        id_ = result
    else:
        id_ = result.get("id", data_dict.get("id"))

    if sender == "resource_view_create":
        activity_type = "new resource view"
    elif sender == "resource_view_update":
        activity_type = "changed resource view"
    else:
        activity_type = "deleted resource view"

    if activity_type != "deleted resource view":
        view = model.ResourceView.get(id_)

        assert view
        view_dict = dictization.table_dictize(view, context)
    else:
        view_dict = {"id": id_, "resource_id": result.get("resource_id")}

    assert view_dict.get('id')
    assert view_dict.get('resource_id')

    # type_ignore_reason: is asserted above, so will have resource_id here.
    resource = model.Resource.get(
        view_dict.get('resource_id'))  # type: ignore
    assert resource

    user_obj = model.User.get(context["user"])
    if user_obj:
        user_id = user_obj.id
    else:
        user_id = "not logged in"

    view_dict['package_id'] = resource.package_id

    activity_dict = {
        "user_id": user_id,
        "object_id": resource.package_id,
        "activity_type": activity_type,
        "data": view_dict,
    }
    activity_create_context = tk.fresh_context(context)
    activity_create_context['ignore_auth'] = True
    tk.get_action("activity_create")(activity_create_context, activity_dict)


# action, context, data_dict, result
def group_or_org_changed(sender: str, **kwargs: Any):
    for key in ("result", "context", "data_dict"):
        if key not in kwargs:
            log.warning("Activity subscription ignored")
            return

    context: types.Context = kwargs["context"]
    result: types.ActionResult.GroupUpdate = kwargs["result"]
    data_dict = kwargs["data_dict"]

    group = model.Group.get(
        result["id"] if result else data_dict["id"]
    )
    if not group:
        raise tk.ObjectNotFound("group")

    type_, action = sender.split("_")

    user_obj = _get_user_or_raise(context["user"])

    activity_dict: dict[str, Any] = {
        "user_id": user_obj.id,
        "object_id": group.id,
    }

    if group.state == "deleted" or action == "delete":
        activity_type = f"deleted {type_}"
    elif action == "create":
        activity_type = f"new {type_}"
    else:
        activity_type = f"changed {type_}"

    activity_dict["activity_type"] = activity_type

    activity_dict["data"] = {
        "group": dictization.table_dictize(group, context)
    }
    activity_create_context = tk.fresh_context(context)
    activity_create_context['ignore_auth'] = True
    tk.get_action("activity_create")(activity_create_context, activity_dict)


# action, context, data_dict, result
def user_changed(sender: str, **kwargs: Any):
    for key in ("result", "context", "data_dict"):
        if key not in kwargs:
            log.warning("Activity subscription ignored")
            return

    context: types.Context = kwargs["context"]
    result: types.ActionResult.UserUpdate = kwargs["result"]

    if sender == "user_create":
        activity_type = "new user"
    else:
        activity_type = "changed user"

    activity_dict = {
        "user_id": result["id"],
        "object_id": result["id"],
        "activity_type": activity_type,
    }
    activity_create_context = tk.fresh_context(context)
    activity_create_context['ignore_auth'] = True
    tk.get_action("activity_create")(activity_create_context, activity_dict)
