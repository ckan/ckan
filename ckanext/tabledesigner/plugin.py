# encoding: utf-8
from __future__ import annotations

from ckan.common import CKANConfig

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from . import views, column_types, interfaces


@toolkit.blanket.actions
@toolkit.blanket.blueprints([views.tabledesigner])
@toolkit.blanket.helpers
class TableDesignerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)

    # IConfigurer

    def update_config(self, config: CKANConfig):
        toolkit.add_template_directory(config, "templates")
        toolkit.add_resource('assets', 'ckanext-tabledesigner')

    # IConfigurable

    def configure(self, config: CKANConfig):
        coltypes = dict(column_types._standard_column_types)
        for plugin in plugins.PluginImplementations(interfaces.IColumnTypes):
            coltypes = plugin.column_types(coltypes)
        column_types.column_types = coltypes
