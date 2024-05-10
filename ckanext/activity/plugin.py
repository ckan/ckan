# -*- coding: utf-8 -*-

from __future__ import annotations

from ckan.common import CKANConfig

import ckan.plugins as p
import ckan.plugins.toolkit as tk

from . import subscriptions
from . import cli


@tk.blanket.auth_functions
@tk.blanket.actions
@tk.blanket.helpers
@tk.blanket.blueprints
@tk.blanket.validators
class ActivityPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ISignal)
    p.implements(p.IClick)

    # IConfigurer
    def update_config(self, config: CKANConfig):
        tk.add_template_directory(config, "templates")
        tk.add_public_directory(config, "public")
        tk.add_resource("assets", "ckanext-activity")

    # ISignal
    def get_signal_subscriptions(self):
        return subscriptions.get_subscriptions()

    # IClick
    def get_commands(self):
        return [cli.activity]
