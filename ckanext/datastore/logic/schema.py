# encoding: utf-8

import json
from typing import Any, cast

import ckan.plugins as p
import ckan.lib.navl.dictization_functions as df
from ckan.types import (
    Context, FlattenDataDict, Schema, FlattenErrorDict,
    FlattenKey, Validator, ValidatorFactory)

get_validator = p.toolkit.get_validator

not_missing = get_validator('not_missing')
not_empty = get_validator('not_empty')
resource_id_exists = get_validator('resource_id_exists')
package_id_exists = get_validator('package_id_exists')
ignore_missing = get_validator('ignore_missing')
empty = get_validator('empty')
boolean_validator = get_validator('boolean_validator')
int_validator = get_validator('int_validator')
one_of = cast(ValidatorFactory, get_validator('one_of'))
unicode_only = get_validator('unicode_only')
default = cast(ValidatorFactory, get_validator('default'))
natural_number_validator = get_validator('natural_number_validator')
configured_default = cast(ValidatorFactory, get_validator(
    'configured_default'))
limit_to_configured_maximum = cast(ValidatorFactory, get_validator(
    'limit_to_configured_maximum'))
unicode_safe = get_validator('unicode_safe')


def rename(old: str, new: str) -> Validator:
    '''
    Rename a schema field from old to new.
    Should be used in __after or __before.
    '''
    def rename_field(key: FlattenKey, data: FlattenDataDict,
                     errors: FlattenErrorDict, context: Context):
        index = max([int(k[1]) for k in data.keys()
                     if len(k) == 3 and k[0] == new] + [-1])

        for field_name in list(data.keys()):
            if field_name[0] == old and data.get(field_name):
                new_field_name = list(field_name)
                new_field_name[0] = new

                if len(new_field_name) > 1:
                    new_field_name[1] = int(new_field_name[1]) + index + 1

                data[tuple(new_field_name)] = data[field_name]
                data.pop(field_name)

    return rename_field


def list_of_strings_or_lists(key: FlattenKey, data: FlattenDataDict,
                             errors: FlattenErrorDict, context: Context):
    value = data.get(key)
    if not isinstance(value, list):
        raise df.Invalid('Not a list')
    for x in value:
        if not isinstance(x, str) and not isinstance(x, list):
            raise df.Invalid('%s: %s' % ('Neither a string nor a list', x))


def list_of_strings_or_string(key: FlattenKey, data: FlattenDataDict,
                              errors: FlattenErrorDict, context: Context):
    value = data.get(key)
    if isinstance(value, str):
        return
    list_of_strings_or_lists(key, data, errors, context)


def json_validator(value: Any) -> Any:
    '''Validate and parse a JSON value.

    dicts and lists will be returned untouched, while other values
    will be run through a JSON parser before being returned. If the
    parsing fails, raise an Invalid exception.
    '''
    if isinstance(value, (list, dict)):
        return value
    try:
        value = json.loads(value)
    except ValueError:
        raise df.Invalid('Cannot parse JSON')
    return value


def unicode_or_json_validator(value: Any) -> Any:
    '''Return a parsed JSON object when applicable, a unicode string when not.

    dicts and None will be returned untouched; otherwise return a JSON object
    if the value can be parsed as such. Return unicode(value) in all other
    cases.
    '''
    try:
        if value is None:
            return value
        v = json_validator(value)
        # json.loads will parse literals; however we want literals as unicode.
        if not isinstance(v, dict):
            return str(value)
        else:
            return v
    except df.Invalid:
        return str(value)


def datastore_create_schema() -> Schema:
    schema = {
        'resource_id': [ignore_missing, unicode_safe, resource_id_exists],
        'force': [ignore_missing, boolean_validator],
        'id': [ignore_missing],
        'aliases': [ignore_missing, list_of_strings_or_string],
        'fields': {
            'id': [not_empty, unicode_safe],
            'type': [ignore_missing],
            'info': [ignore_missing],
        },
        'primary_key': [ignore_missing, list_of_strings_or_string],
        'indexes': [ignore_missing, list_of_strings_or_string],
        'triggers': {
            'when': [
                default(u'before insert or update'),
                unicode_only,
                one_of([u'before insert or update'])],
            'for_each': [
                default(u'row'),
                unicode_only,
                one_of([u'row'])],
            'function': [not_empty, unicode_only],
        },
        'calculate_record_count': [ignore_missing, default(False),
                                   boolean_validator],
        '__junk': [empty],
        '__before': [rename('id', 'resource_id')]
    }
    return schema


def datastore_upsert_schema() -> Schema:
    schema = {
        'resource_id': [not_missing, not_empty, unicode_safe],
        'force': [ignore_missing, boolean_validator],
        'id': [ignore_missing],
        'method': [ignore_missing, unicode_safe, one_of(
            ['upsert', 'insert', 'update'])],
        'calculate_record_count': [ignore_missing, default(False),
                                   boolean_validator],
        'dry_run': [ignore_missing, boolean_validator],
        '__junk': [empty],
        '__before': [rename('id', 'resource_id')]
    }
    return schema


def datastore_delete_schema() -> Schema:
    schema = {
        'resource_id': [not_missing, not_empty, unicode_safe],
        'force': [ignore_missing, boolean_validator],
        'id': [ignore_missing],
        'calculate_record_count': [ignore_missing, default(False),
                                   boolean_validator],
        '__junk': [empty],
        '__before': [rename('id', 'resource_id')]
    }
    return schema


def datastore_search_schema() -> Schema:
    schema = {
        'resource_id': [not_missing, not_empty, unicode_safe],
        'id': [ignore_missing],
        'q': [ignore_missing, unicode_or_json_validator],
        'plain': [ignore_missing, boolean_validator],
        'filters': [ignore_missing, json_validator],
        'language': [ignore_missing, unicode_safe],
        'limit': [
            configured_default('ckan.datastore.search.rows_default', 100),
            natural_number_validator,
            limit_to_configured_maximum('ckan.datastore.search.rows_max',
                                        32000)],
        'offset': [ignore_missing, int_validator],
        'fields': [ignore_missing, list_of_strings_or_string],
        'sort': [ignore_missing, list_of_strings_or_string],
        'distinct': [ignore_missing, boolean_validator],
        'include_total': [default(True), boolean_validator],
        'total_estimation_threshold': [default(None), int_validator],
        'records_format': [
            default(u'objects'),
            one_of([u'objects', u'lists', u'csv', u'tsv'])],
        '__junk': [empty],
        '__before': [rename('id', 'resource_id')],
        'full_text': [ignore_missing, unicode_safe]
    }
    return schema


def datastore_function_create_schema() -> Schema:
    return {
        'name': [unicode_only, not_empty],
        'or_replace': [default(False), boolean_validator],
        # we're only exposing functions for triggers at the moment
        'arguments': {
            'argname': [unicode_only, not_empty],
            'argtype': [unicode_only, not_empty],
        },
        'rettype': [default(u'void'), unicode_only],
        'definition': [unicode_only],
    }


def datastore_function_delete_schema() -> Schema:
    return {
        'name': [unicode_only, not_empty],
        'if_exists': [default(False), boolean_validator],
    }


def datastore_analyze_schema() -> Schema:
    return {
        'resource_id': [unicode_safe, resource_id_exists],
    }
