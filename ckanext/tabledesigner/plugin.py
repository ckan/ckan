# encoding: utf-8
from __future__ import annotations

from ckan.common import CKANConfig

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.tabledesigner.views as views


@toolkit.blanket.actions
@toolkit.blanket.blueprints([views.tabledesigner])
@toolkit.blanket.helpers
class TableDesignerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config: CKANConfig):
        toolkit.add_template_directory(config, "templates")
        toolkit.add_resource('assets', 'ckanext-tabledesigner')
