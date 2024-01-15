# encoding: utf-8

from __future__ import annotations

from typing import Any
from ckan.types import (
    Schema, Context, FlattenErrorDict, FlattenDataDict, FlattenKey
)
from ckan.common import CKANConfig

import json

from ckan.plugins.toolkit import Invalid, get_validator, add_template_directory
from ckan import plugins
from ckanext.datastore.interfaces import IDataDictionaryForm


class ExampleIDataDictionaryFormPlugin(plugins.SingletonPlugin):
    plugins.implements(IDataDictionaryForm)
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config: CKANConfig):
        add_template_directory(config, 'templates')

    # IDataDictionaryForm

    def update_datastore_create_schema(self, schema: Schema):
        ignore_empty = get_validator('ignore_empty')
        int_validator = get_validator('int_validator')

        assert isinstance(schema['fields'], dict)
        f = schema['fields']
        f['an_int'] = [ignore_empty, int_validator, to_plugin_data()]
        f['json_obj'] = [ignore_empty, json_obj, to_plugin_data()]
        # use different plugin_key so that value isn't removed
        # when above fields are updated
        f['secret'] = [
            ignore_empty,
            to_plugin_data('example_idatadictionaryform_secrets')]
        return schema

    def update_datastore_info_field(
            self, field: dict[str, Any], plugin_data: dict[str, Any]):
        # expose all our non-secret plugin data in the field
        field.update(plugin_data.get('example_idatadictionaryform', {}))
        return field


def json_obj(value: str | dict[str, Any]) -> dict[str, Any]:
    try:
        if isinstance(value, str):
            value = json.loads(value)
        else:
            json.dumps(value)
        if not isinstance(value, dict):
            raise TypeError
        return value
    except (TypeError, ValueError):
        raise Invalid('Not a JSON object')


def to_plugin_data(plugin_key: str='example_idatadictionaryform'):
    def validator(
            key: FlattenKey,
            data: FlattenDataDict,
            errors: FlattenErrorDict,
            context: Context):
        """
        move value to plugin_data dict
        """
        value = data.pop(key)
        field_index = key[-2]
        field_name = key[-1]
        context['plugin_data'].setdefault(
            field_index, {}).setdefault(
            plugin_key, {})[field_name] = value
    return validator
