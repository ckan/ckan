# encoding: utf-8
from __future__ import annotations

from typing import List, Type, cast

from ckan.common import CKANConfig
from ckan.types import Schema, ValidatorFactory
import ckan.plugins as p
from ckan.plugins.toolkit import (
    blanket, add_template_directory, add_resource, get_validator,
)
from ckanext.datastore.interfaces import IDataDictionaryForm

from . import views, interfaces, validators
from .column_types import ColumnType, _standard_column_types
from .column_constraints import ColumnConstraint, _standard_column_constraints


_column_types: dict[str, Type[ColumnType]] = {}
_column_constraints: dict[str, List[Type[ColumnConstraint]]] = {}


@blanket.actions
@blanket.blueprints([views.tabledesigner])
@blanket.helpers
@blanket.validators(validators)
class TableDesignerPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IConfigurable)
    p.implements(IDataDictionaryForm)

    # IConfigurer

    def update_config(self, config: CKANConfig):
        add_template_directory(config, "templates")
        add_resource('assets', 'ckanext-tabledesigner')

    # IConfigurable

    def configure(self, config: CKANConfig):
        coltypes = dict(_standard_column_types)
        for plugin in p.PluginImplementations(interfaces.IColumnTypes):
            coltypes = plugin.column_types(coltypes)

        _column_types.clear()
        _column_types.update(coltypes)

        colcons = {
            key: list(val) for key, val
            in _standard_column_constraints.items()
        }
        for plugin in p.PluginImplementations(interfaces.IColumnConstraints):
            colcons = plugin.column_constraints(colcons, _column_types)

        _column_constraints.clear()
        _column_constraints.update(colcons)

    # IDataDictionaryForm

    def update_datastore_create_schema(self, schema: Schema):
        not_empty = get_validator('not_empty')
        OneOf = cast(ValidatorFactory, get_validator('OneOf'))
        default = cast(ValidatorFactory, get_validator('default'))
        td_ignore = get_validator('tabledesigner_ignore')
        to_datastore_plugin_data = cast(
            ValidatorFactory, get_validator('to_datastore_plugin_data'))
        td_pd = to_datastore_plugin_data('tabledesigner')

        f = cast(Schema, schema['fields'])
        f['tdtype'] = [td_ignore, not_empty, OneOf(_column_types), td_pd]
        f['tdpkreq'] = [
            td_ignore, default(''), OneOf(['', 'req', 'pk']), td_pd]
        for ct in _column_types.values():
            f.update(ct.datastore_field_schema(td_ignore, td_pd))
        for cc in dict.fromkeys(  # deduplicate column constraints
                cc for ccl in _column_constraints.values() for cc in ccl):
            f.update(cc.datastore_field_schema(td_ignore, td_pd))
        return schema

    def update_datastore_info_field(
            self, field: dict[str, Any], plugin_data: dict[str, Any]):
        # expose all our plugin data in the field
        field.update(plugin_data.get('tabledesigner', {}))
        return field
