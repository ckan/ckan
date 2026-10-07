# encoding: utf-8
from __future__ import annotations

from ckan.types import (
    Context, FlattenDataDict, FlattenKey, FlattenErrorDict, Any,
)
from ckan.plugins.toolkit import missing, Invalid, _

from ckanext.datastore.helpers import is_valid_field_name


SYSTEM_COLUMN_NAMES = ('tableoid', 'xmin', 'cmin', 'xmax', 'cmax', 'ctid')


def to_datastore_plugin_data(plugin_key: str):
    """
    Return a validator that will move values from data to
    context['plugin_data'][field_index][plugin_key][field_name]

    where field_index is the field number, plugin_key (passed to this
    function) is typically set to the plugin name and field name is the
    original field name being validated.
    """

    def validator(
            key: FlattenKey,
            data: FlattenDataDict,
            errors: FlattenErrorDict,
            context: Context):
        value = data.pop(key)
        field_index = key[-2]
        field_name = key[-1]
        context['plugin_data'].setdefault(
            field_index, {}).setdefault(
            plugin_key, {})[field_name] = value
    return validator


def datastore_default_current(
        key: FlattenKey, data: FlattenDataDict,
        errors: FlattenErrorDict, context: Context):
    '''default to currently stored value if empty or missing'''
    value = data[key]
    if value is not None and value != '' and value is not missing:
        return
    field_index = key[-2]
    field_name = key[-1]
    # current values for plugin_data are available as
    # context['plugin_data'][field_index]['_current']
    current = context['plugin_data'].get(field_index, {}).get(
        '_current', {}).get('example_idatadictionaryform', {}).get(
        field_name)
    if current:
        data[key] = current


def datastore_field_name(value: Any, context: Context) -> Any:
    """
    Check if the field name is valid
    """
    if not is_valid_field_name(value):
        raise Invalid(_('"{0}" is not a valid field name').format(value))
    if value in SYSTEM_COLUMN_NAMES:
        raise Invalid(_('"{0}" conflicts with a system column name').format(value))
    return value
