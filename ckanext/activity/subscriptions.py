# -*- coding: utf-8 -*-

from __future__ import annotations
import logging
from typing import Any

import ckan.plugins.toolkit as tk
import ckan.lib.dictization as dictization

from ckan import types
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

    context: types.Context = kwargs["context"]
    datasets = kwargs["data_dict"].get("datasets")
    model = context["model"]

    user = context["user"]
    user_obj = model.User.get(user)
    if user_obj:
        user_id = user_obj.id
    else:
        user_id = "not logged in"
    for dataset in datasets:
        entity = model.Package.get(dataset)
        assert entity

        activity = Activity.activity_stream_item(entity, "changed", user_id)
        model.Session.add(activity)

    if not context.get("defer_commit"):
        model.Session.commit()


# action, context, data_dict, result
def package_changed(sender: str, **kwargs: Any):
    for key in ("result", "context", "data_dict"):
        if key not in kwargs:
            log.warning("Activity subscription ignored")
            return

    type_ = "new" if sender == "package_create" else "changed"

    context: types.Context = kwargs["context"]
    result: types.ActionResult.PackageUpdate = kwargs["result"]
    data_dict = kwargs["data_dict"]

    if not result:
        id_ = data_dict["id"]
    elif isinstance(result, str):
        id_ = result
    else:
        id_ = result["id"]

    pkg = context["model"].Package.get(id_)
    assert pkg

    if pkg.private:
        return

    user_obj = context["model"].User.get(context["user"])
    if user_obj:
        user_id = user_obj.id
    else:
        user_id = "not logged in"

    activity = Activity.activity_stream_item(pkg, type_, user_id)
    context["session"].add(activity)
    if not context.get("defer_commit"):
        context["session"].commit()


# action, context, data_dict, result
def group_or_org_changed(sender: str, **kwargs: Any):
    for key in ("result", "context", "data_dict"):
        if key not in kwargs:
            log.warning("Activity subscription ignored")
            return

    context: types.Context = kwargs["context"]
    result: types.ActionResult.GroupUpdate = kwargs["result"]
    data_dict = kwargs["data_dict"]

    group = context["model"].Group.get(
        result["id"] if result else data_dict["id"]
    )
    assert group

    type_, action = sender.split("_")

    user_obj = context["model"].User.get(context["user"])
    assert user_obj

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
