from __future__ import annotations

from . import validator_args
from ckan.types import Validator, ValidatorFactory, Schema
from ckan.common import config


@validator_args
def file_create(  # noqa: PLR0913
    ignore_empty: Validator,
    unicode_only: Validator,
    default: ValidatorFactory,
    into_upload: Validator,
    not_missing: Validator,
) -> Schema:
    # name is checked inside action, using "upload" as source if empty
    return {
        "name": [ignore_empty, unicode_only],
        "storage": [
            default(config["ckan.files.default_storages.default"]),
            unicode_only,
        ],
        "upload": [not_missing, into_upload],
    }


@validator_args
def file_register(
    default: ValidatorFactory,
    unicode_only: Validator,
    not_missing: Validator,
) -> Schema:
    return {
        "location": [not_missing, unicode_only],
        "storage": [
            default(config["ckan.files.default_storages.default"]),
            unicode_only,
        ],
    }


@validator_args
def file_search(
    default: ValidatorFactory,
    int_validator: Validator,
    dict_only: Validator,
    convert_to_json_if_string: Validator,
) -> Schema:
    return {
        "start": [default(0), int_validator],
        "rows": [default(10), int_validator],
        "sort": [default("name")],
        "filters": [default("{}"), convert_to_json_if_string, dict_only],
    }


@validator_args
def file_delete(not_empty: Validator, unicode_only: Validator) -> Schema:
    return {"id": [not_empty, unicode_only]}


@validator_args
def file_show(not_empty: Validator, unicode_only: Validator) -> Schema:
    return {"id": [not_empty, unicode_only]}


@validator_args
def file_rename(not_empty: Validator, unicode_only: Validator) -> Schema:
    return {"id": [not_empty, unicode_only], "name": [not_empty, unicode_only]}


@validator_args
def file_pin(not_empty: Validator, unicode_only: Validator) -> Schema:
    return {"id": [not_empty, unicode_only]}


@validator_args
def file_unpin(not_empty: Validator, unicode_only: Validator) -> Schema:
    return {"id": [not_empty, unicode_only]}


@validator_args
def ownership_transfer(
    not_empty: Validator,
    boolean_validator: Validator,
    default: ValidatorFactory,
    unicode_only: Validator,
) -> Schema:
    return {
        "id": [not_empty, unicode_only],
        "owner_id": [not_empty, unicode_only],
        "owner_type": [not_empty, unicode_only],
        "force": [default(False), boolean_validator],
        "pin": [default(False), boolean_validator],
    }


@validator_args
def owner_scan(
    default: ValidatorFactory, unicode_only: Validator, ignore_missing: Validator
) -> Schema:
    return {
        "owner_id": [default(""), unicode_only],
        "owner_type": [default("user"), unicode_only],
        "start": [ignore_missing],
        "rows": [ignore_missing],
        "sort": [ignore_missing],
    }
