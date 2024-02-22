# encoding: utf-8

from __future__ import annotations

from typing import Any, cast
from ckan.types import Schema, ValidatorFactory
from ckan.common import CKANConfig
from ckan.types import (
    Context, FlattenDataDict, FlattenErrorDict, FlattenKey,
)

import json

from ckan.plugins.toolkit import (
    Invalid, get_validator, add_template_directory, _, missing,
)
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
        unicode_only = get_validator('unicode_only')
        datastore_default_current = get_validator('datastore_default_current')
        to_datastore_plugin_data = cast(
            ValidatorFactory, get_validator('to_datastore_plugin_data'))
        to_eg_iddf = to_datastore_plugin_data('example_idatadictionaryform')

        f = cast(Schema, schema['fields'])
        f['an_int'] = [ignore_empty, int_validator, to_eg_iddf]
        f['json_obj'] = [ignore_empty, json_obj, to_eg_iddf]
        f['only_up'] = [
            only_increasing, ignore_empty, int_validator, to_eg_iddf]
        f['sticky'] = [
            datastore_default_current, ignore_empty, unicode_only, to_eg_iddf]

        # use different plugin_key so that value isn't removed
        # when above fields are updated & value not exposed in
        # datastore_info
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
    '''accept only json objects i.e. dicts or "{...}"'''
    try:
        if isinstance(value, str):
            value = json.loads(value)
        else:
            json.dumps(value)
        if not isinstance(value, dict):
            raise TypeError
        return value
    except (TypeError, ValueError):
        raise Invalid(_('Not a JSON object'))


def only_increasing(
        key: FlattenKey, data: FlattenDataDict,
        errors: FlattenErrorDict, context: Context):
    '''once set only accept new values larger than current value'''
    value = data[key]
    field_index = key[-2]
    field_name = key[-1]
    # current values for plugin_data are available as
    # context['plugin_data'][field_index]['_current']
    current = context['plugin_data'].get(field_index, {}).get(
        '_current', {}).get('example_idatadictionaryform', {}).get(
        field_name)
    if current is None:
        return
    if value is not None and value != '' and value is not missing:
        try:
            if int(value) < current:
                errors[key].append(
                    _('Value must be larger than %d') % current)
        except ValueError:
            return  # allow int_validator to handle the error
    else:
        # keep current value when empty/missing
        data[key] = current
