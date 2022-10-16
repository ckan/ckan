# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import cast

from ckan.logic.schema import validator_args, default_pagination_schema
from ckan.types import Schema, Validator, ValidatorFactory


@validator_args
def default_create_activity_schema(
    ignore: Validator,
    not_missing: Validator,
    not_empty: Validator,
    unicode_safe: Validator,
    convert_user_name_or_id_to_id: Validator,
    object_id_validator: Validator,
    activity_type_exists: Validator,
    ignore_empty: Validator,
    ignore_missing: Validator,
):
    return cast(
        Schema,
        {
            "id": [ignore],
            "timestamp": [ignore],
            "user_id": [
                not_missing,
                not_empty,
                unicode_safe,
                convert_user_name_or_id_to_id,
            ],
            "object_id": [
                not_missing,
                not_empty,
                unicode_safe,
                object_id_validator,
            ],
            "activity_type": [
                not_missing,
                not_empty,
                unicode_safe,
                activity_type_exists,
            ],
            "data": [ignore_empty, ignore_missing],
        },
    )


@validator_args
def default_dashboard_activity_list_schema(
    configured_default: ValidatorFactory,
    natural_number_validator: Validator,
    limit_to_configured_maximum: ValidatorFactory,
    ignore_missing: Validator,
    datetime_from_timestamp_validator: Validator,

):
    schema = default_pagination_schema()
    schema["limit"] = [
        configured_default("ckan.activity_list_limit", 31),
        natural_number_validator,
        limit_to_configured_maximum("ckan.activity_list_limit_max", 100),
    ]
    schema["before"] = [ignore_missing, datetime_from_timestamp_validator]
    schema["after"] = [ignore_missing, datetime_from_timestamp_validator]
    return schema


@validator_args
def default_activity_list_schema(
    not_missing: Validator,
    unicode_safe: Validator,
    configured_default: ValidatorFactory,
    natural_number_validator: Validator,
    limit_to_configured_maximum: ValidatorFactory,
    ignore_missing: Validator,
    boolean_validator: Validator,
    ignore_not_sysadmin: Validator,
    list_of_strings: Validator,
    datetime_from_timestamp_validator: Validator,
):

    schema = default_pagination_schema()
    schema["id"] = [not_missing, unicode_safe]
    schema["limit"] = [
        configured_default("ckan.activity_list_limit", 31),
        natural_number_validator,
        limit_to_configured_maximum("ckan.activity_list_limit_max", 100),
    ]
    schema["include_hidden_activity"] = [
        ignore_missing,
        ignore_not_sysadmin,
        boolean_validator,
    ]
    schema["activity_types"] = [ignore_missing, list_of_strings]
    schema["exclude_activity_types"] = [ignore_missing, list_of_strings]
    schema["before"] = [ignore_missing, datetime_from_timestamp_validator]
    schema["after"] = [ignore_missing, datetime_from_timestamp_validator]

    return schema
