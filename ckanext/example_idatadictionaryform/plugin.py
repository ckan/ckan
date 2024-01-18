# encoding: utf-8

from __future__ import annotations

from typing import Any, cast
from ckan.types import Schema, ValidatorFactory
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
        to_datastore_plugin_data = cast(
            ValidatorFactory, get_validator('to_datastore_plugin_data'))
        to_eg_iddf = to_datastore_plugin_data('example_idatadictionaryform')

        f = cast(Schema, schema['fields'])
        f['an_int'] = [ignore_empty, int_validator, to_eg_iddf]
        f['json_obj'] = [ignore_empty, json_obj, to_eg_iddf]

        # use different plugin_key so that value isn't removed
        # when above fields are updated
        f['secret'] = [
            ignore_empty,
            to_datastore_plugin_data('example_idatadictionaryform_secret')
        ]
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
