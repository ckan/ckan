# -*- coding: utf-8 -*-

import logging
import enum
import types

from functools import update_wrapper
from importlib import import_module

import ckan.plugins as p

log = logging.getLogger(__name__)


class Blanket(enum.IntEnum):
    helper = 1 << 0
    auth = 1 << 1
    action = 1 << 2
    blueprint = 1 << 3
    cli = 1 << 4
    all = helper | auth | action | blueprint | cli

    def path(self):
        return self._paths[self]

    def method(self):
        return self._methods[self]

    def interface(self):
        return self._interfaces[self]

    def returns_list(self):
        return self & (Blanket.cli | Blanket.blueprint)

    def implement(self, locals, plugin, subject):
        if subject is None:
            root = plugin.__module__[: plugin.__module__.rindex(u".")]
            import_path = u".".join([root, self.path()])
            try:
                subject = import_module(import_path)
            except ImportError:
                log.debug(
                    u"Unable to import <%s> for "
                    u"blanket implementation of %s for %s",
                    import_path,
                    self.interface().__name__,
                    plugin.__name__,
                )
                return

        locals[self.method()] = _as_implementation(
            subject, self.returns_list()
        )


Blanket._paths = {
    Blanket.helper: u"helpers",
    Blanket.auth: u"logic.auth",
    Blanket.action: u"logic.action",
    Blanket.blueprint: u"views",
    Blanket.cli: u"cli",
}

Blanket._methods = {
    Blanket.helper: u"get_helpers",
    Blanket.auth: u"get_auth_functions",
    Blanket.action: u"get_actions",
    Blanket.blueprint: u"get_blueprint",
    Blanket.cli: u"get_commands",
}

Blanket._interfaces = {
    Blanket.helper: p.ITemplateHelpers,
    Blanket.auth: p.IAuthFunctions,
    Blanket.action: p.IActions,
    Blanket.blueprint: p.IBlueprint,
    Blanket.cli: p.IClick,
}


def _as_implementation(subject, as_list):
    def func(self, *args, **kwargs):
        if isinstance(subject, types.FunctionType):
            return subject(*args, **kwargs)
        elif isinstance(subject, types.ModuleType):
            result = {
                item: getattr(subject, item)
                for item in getattr(subject, u"__all__", [])
            }
            if as_list:
                return list(result.values())
            return result
        else:
            return subject

    return func


def blanket_implementation(group=Blanket.all, subject=None):
    def wrapper(plugin):
        class wrapped_plugin(plugin):
            for key in Blanket:
                if key is Blanket.all:
                    continue
                if key & group:
                    p.implements(key.interface())
                    key.implement(locals(), plugin, subject)

        return update_wrapper(wrapped_plugin, plugin, updated=[])

    return wrapper
