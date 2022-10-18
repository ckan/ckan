# -*- coding: utf-8 -*-

from __future__ import annotations

from ckan.common import CKANConfig

import ckan.plugins as p
import ckan.plugins.toolkit as tk

from . import subscriptions, helpers


@tk.blanket.auth_functions
@tk.blanket.actions
@tk.blanket.helpers
@tk.blanket.blueprints
@tk.blanket.validators
class ActivityPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.ISignal)

    # IConfigurer
    def update_config(self, config: CKANConfig):
        tk.add_template_directory(config, "templates")
        tk.add_resource("assets", "ckanext-activity")

    # ISignal
    def get_signal_subscriptions(self):
        return subscriptions.get_subscriptions()

    # ITemplateHelpers
    def get_helpers(self):
        return {"get_pkg_title_from_id": helpers.get_pkg_title_from_id}