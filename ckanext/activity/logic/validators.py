# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Any, cast

import ckan.plugins.toolkit as tk

from ckan.types import (
    FlattenDataDict,
    FlattenKey,
    Context,
    FlattenErrorDict,
    ContextValidator,
)


def activity_type_exists(activity_type: Any) -> Any:
    """Raises Invalid if there is no registered activity renderer for the
    given activity_type. Otherwise returns the given activity_type.

    This just uses object_id_validators as a lookup.
    very safe.

    """
    if activity_type in object_id_validators:
        return activity_type
    else:
        raise tk.Invalid("%s: %s" % (tk._("Not found"), tk._("Activity type")))


VALIDATORS_PACKAGE_ACTIVITY_TYPES = {
    "new package": "package_id_exists",
    "changed package": "package_id_exists",
    "deleted package": "package_id_exists",
    "follow dataset": "package_id_exists",
}

VALIDATORS_USER_ACTIVITY_TYPES = {
    "new user": "user_id_exists",
    "changed user": "user_id_exists",
    "follow user": "user_id_exists",
}

VALIDATORS_GROUP_ACTIVITY_TYPES = {
    "new group": "group_id_exists",
    "changed group": "group_id_exists",
    "deleted group": "group_id_exists",
    "follow group": "group_id_exists",
}

VALIDATORS_ORGANIZATION_ACTIVITY_TYPES = {
    "new organization": "group_id_exists",
    "changed organization": "group_id_exists",
    "deleted organization": "group_id_exists",
    "follow organization": "group_id_exists",
}

# A dictionary mapping activity_type values from activity dicts to functions
# for validating the object_id values from those same activity dicts.
object_id_validators = {
    **VALIDATORS_PACKAGE_ACTIVITY_TYPES,
    **VALIDATORS_USER_ACTIVITY_TYPES,
    **VALIDATORS_GROUP_ACTIVITY_TYPES,
    **VALIDATORS_ORGANIZATION_ACTIVITY_TYPES
}


def object_id_validator(
    key: FlattenKey,
    activity_dict: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
) -> Any:
    """Validate the 'object_id' value of an activity_dict.

    Uses the object_id_validators dict (above) to find and call an 'object_id'
    validator function for the given activity_dict's 'activity_type' value.

    Raises Invalid if the model given in context contains no object of the
    correct type (according to the 'activity_type' value of the activity_dict)
    with the given ID.

    Raises Invalid if there is no object_id_validator for the activity_dict's
    'activity_type' value.

    """
    activity_type = activity_dict[("activity_type",)]
    if activity_type in object_id_validators:
        object_id = activity_dict[("object_id",)]
        name = object_id_validators[activity_type]
        validator = cast(ContextValidator, tk.get_validator(name))
        return validator(object_id, context)
    else:
        raise tk.Invalid(
            'There is no object_id validator for activity type "%s"'
            % activity_type
        )
