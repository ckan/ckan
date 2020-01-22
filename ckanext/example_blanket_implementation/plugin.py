# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckanext.example_blanket_implementation as current
from ckanext.example_blanket_implementation.logic import auth, action


@tk.blanket_implementation()
class ExampleBlanketPlugin(p.SingletonPlugin):
    pass


@tk.blanket_implementation(tk.Blanket.helper)
class ExampleBlanketHelperPlugin(p.SingletonPlugin):
    pass


@tk.blanket_implementation(tk.Blanket.auth, auth)
class ExampleBlanketAuthPlugin(p.SingletonPlugin):
    pass


@tk.blanket_implementation(tk.Blanket.action, action.get_actions)
class ExampleBlanketActionPlugin(p.SingletonPlugin):
    pass


@tk.blanket_implementation(
    tk.Blanket.blueprint, lambda: current.views.get_blueprints()
)
class ExampleBlanketBlueprintPlugin(p.SingletonPlugin):
    pass


@tk.blanket_implementation(tk.Blanket.cli)
class ExampleBlanketCliPlugin(p.SingletonPlugin):
    pass
