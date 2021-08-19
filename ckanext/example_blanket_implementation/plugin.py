# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckanext.example_blanket_implementation as current
from ckanext.example_blanket_implementation.logic import auth, action
from ckanext.example_blanket_implementation.logic.validators import is_blanket

_validators = {u'is_blanket': is_blanket}


# As an alternative, `@tk.blanket._everything` may be used, though
# it's not recommended, because in future new blanket groups will be
# added and existing functionality can become broken. It's generally
# can be used for testing and prototyping, and replaced with explicit
# blankets before going to production
@tk.blanket.helper
@tk.blanket.auth_function
@tk.blanket.action
@tk.blanket.blueprint
@tk.blanket.cli
@tk.blanket.validator
class ExampleBlanketPlugin(p.SingletonPlugin):
    pass


@tk.blanket.helper
class ExampleBlanketHelperPlugin(p.SingletonPlugin):
    pass


@tk.blanket.auth_function(auth)
class ExampleBlanketAuthPlugin(p.SingletonPlugin):
    pass


@tk.blanket.action(action.get_actions)
class ExampleBlanketActionPlugin(p.SingletonPlugin):
    pass


@tk.blanket.blueprint(lambda: current.views.get_blueprints())
class ExampleBlanketBlueprintPlugin(p.SingletonPlugin):
    pass


@tk.blanket.cli
class ExampleBlanketCliPlugin(p.SingletonPlugin):
    pass


@tk.blanket.validator(_validators)
class ExampleBlanketValidatorPlugin(p.SingletonPlugin):
    pass
