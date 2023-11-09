# encoding: utf-8
from __future__ import annotations

from typing import List, Type

from ckan.common import CKANConfig

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit

from . import views, interfaces
from .column_types import ColumnType, _standard_column_types
from .column_constraints import ColumnConstraint, _standard_column_constraints


_column_types: dict[str, Type[ColumnType]] = {}
_column_constraints: dict[str, List[Type[ColumnConstraint]]] = {}


@toolkit.blanket.actions
@toolkit.blanket.blueprints([views.tabledesigner])
@toolkit.blanket.helpers
class TableDesignerPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IConfigurable)

    # IConfigurer

    def update_config(self, config: CKANConfig):
        toolkit.add_template_directory(config, "templates")
        toolkit.add_resource('assets', 'ckanext-tabledesigner')

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
            colcons = plugin.column_types(colcons)

        _column_constraints.clear()
        _column_constraints.update(colcons)
