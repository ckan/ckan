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
    user_id = activity_dict["user_id"]
    object_id = activity_dict["object_id"]
    activity_type = activity_dict["activity_type"]
    if "data" in activity_dict:
        data = activity_dict["data"]
    else:
        data = None
    activity_obj = Activity(user_id, object_id, activity_type, data)
    session.add(activity_obj)
    return activity_obj
