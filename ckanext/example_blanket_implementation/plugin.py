# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckanext.example_blanket_implementation as current
from ckanext.example_blanket_implementation.logic import auth, action
from ckanext.example_blanket_implementation.logic.validators import is_blanket

_validators = {u"is_blanket": is_blanket}


@tk.blanket.helpers
@tk.blanket.auth_functions
@tk.blanket.actions
@tk.blanket.blueprints
@tk.blanket.cli
@tk.blanket.validators
class ExampleBlanketPlugin(p.SingletonPlugin):
    pass


@tk.blanket.helpers
class ExampleBlanketHelperPlugin(p.SingletonPlugin):
    pass


@tk.blanket.auth_functions(auth)
class ExampleBlanketAuthPlugin(p.SingletonPlugin):
    pass


@tk.blanket.actions(action.get_actions)
class ExampleBlanketActionPlugin(p.SingletonPlugin):
    pass


@tk.blanket.blueprints(lambda: current.views.get_blueprints())
class ExampleBlanketBlueprintPlugin(p.SingletonPlugin):
    pass


@tk.blanket.cli
class ExampleBlanketCliPlugin(p.SingletonPlugin):
    pass


@tk.blanket.validators(_validators)
class ExampleBlanketValidatorPlugin(p.SingletonPlugin):
    pass
