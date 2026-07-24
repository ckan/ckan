# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Any

from ckan.types import Context

from .activity import Activity


__all__ = ["Activity"]


def activity_dict_save(
    activity_dict: dict[str, Any], context: Context
) -> "Activity":

    session = context["session"]

    activity_obj = Activity(
        activity_dict["user_id"],
        activity_dict["object_id"],
        activity_dict["activity_type"],
        activity_dict.get("data"),
        activity_dict.get("permission_labels"),
    )
    session.add(activity_obj)
    return activity_obj
