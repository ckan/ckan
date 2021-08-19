# -*- coding: utf-8 -*-

"""Quick implementations for simplest interfaces.

Decorate plugin with ``@tk.blanket.<GROUP>`` and it will automatically
receive common implementation of interface corresponding to the chosen
group. Common implementation is the one, that satisfies following
requirements:

 - implementation of interface must provide just a single method
 - method, required by interface, returns either list or dictionary
 - all the items, that are returned from method are defined in separate module
 - all the items(and only those items) are listed inside ``module.__all__``
 - module is available under common import path. Those paths are:

   - ``ckanext.ext.helpers`` for ``ITemplateHelpers``
   - ``ckanext.ext.logic.auth`` for ``IAuthFunctions``
   - ``ckanext.ext.logic.action`` for ``IActions``
   - ``ckanext.ext.logic.validators`` for ``IValidators``
   - ``ckanext.ext.views`` for ``IBlueprint``
   - ``ckanext.ext.cli`` for ``IClick``

Available groups are:
  - ``tk.blanket.helpers``: implemets ``ITemplateHelpers``
  - ``tk.blanket.auth``: implemets ``IAuthFunctions``
  - ``tk.blanket.action``: implemets ``IActions``
  - ``tk.blanket.validator``: implemets ``IValidators``
  - ``tk.blanket.blueprint``: implemets ``IBlueprint``
  - ``tk.blanket.cli``: implemets ``IClick``

Example::

    @tk.blanket.action
    class MyPlugin(plugins.SingletonPlugin):
        pass

Is roughly equal to::

    class MyPlugin(plugins.SingletonPlugin):
        plugins.implements(plugins.IActions)

        def get_actions(self):
            import ckanext.ext.logic.action as actions
            extra_actions = {
                name: getattr(actions, name)
                for name in actions.__all__
            }
            return extra_actions

In addition, if plugin follows custom naming conventions, it's
possible to customize implementation, by providing argument to
decorator.

If extension uses different names for modules::

    import ckanext.ext.custom_actions as custom_module

    @tk.blanket.action(custom_module)
    class MyPlugin(plugins.SingletonPlugin):
        pass

If extension already defines function that returns items required by
interface::

    def all_actions():
        return {'ext_action': ext_action}

    @tk.blanket.action(all_actions)
    class MyPlugin(plugins.SingletonPlugin):
        pass

If extension statically defines collection of items required by
interface::

    all_actions = {'ext_action': ext_action}

    @tk.blanket.action(all_actions)
    class MyPlugin(plugins.SingletonPlugin):
        pass

"""
import logging
import enum
import types

from functools import update_wrapper
from importlib import import_module
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Type, Union

import ckan.plugins as p

__all__ = [u"helper", u"auth", u"action", u"blueprint", u"cli", u"validator"]

log = logging.getLogger(__name__)

Subject = Union[
    types.FunctionType, types.ModuleType, Dict[str, Any], List[Any]
]


class Blanket(enum.Flag):
    """Enumeration of all available blanket types.

    In addition, contains hidden `_all` option, that contains all
    other types. This option is experimental and shouldn't be used
    outside current module, as it can be removed in future.

    """

    helper = enum.auto()
    auth = enum.auto()
    action = enum.auto()
    blueprint = enum.auto()
    cli = enum.auto()
    validator = enum.auto()
    _all = helper | auth | action | blueprint | cli | validator

    def path(self) -> str:
        """Return relative(start from `ckanext.ext`) import path for
        implementation.

        """
        return _mapping[self].path

    def method(self) -> str:
        """Return the name of the method, required for implementation."""
        return _mapping[self].method

    def interface(self) -> p.Interface:
        """Return interface provided by blanket."""
        return _mapping[self].interface

    def returns_list(self) -> bool:
        """Check, whether implementation returns list instead of dict."""
        return bool(self & (Blanket.cli | Blanket.blueprint))

    def implement(
        self,
        locals: Dict[str, Any],
        plugin: p.SingletonPlugin,
        subject: Optional[Subject],
    ):
        """Provide implementation for interface."""
        if subject is None:
            _last_dot = plugin.__module__.rindex(u".")
            root = plugin.__module__[:_last_dot]
            import_path = u".".join([root, self.path()])
            try:
                subject = import_module(import_path)
            except ImportError:
                log.error(
                    u"Unable to import <%s> for "
                    u"blanket implementation of %s for %s",
                    import_path,
                    self.interface().__name__,
                    plugin.__name__,
                )
                raise
        locals[self.method()] = _as_implementation(
            subject, self.returns_list()
        )


class BlanketMapping(NamedTuple):
    path: str
    method: str
    interface: p.Interface


_mapping: Dict[Blanket, BlanketMapping] = {
    Blanket.helper: BlanketMapping(
        u"helpers", u"get_helpers", p.ITemplateHelpers
    ),
    Blanket.auth: BlanketMapping(
        u"logic.auth", u"get_auth_functions", p.IAuthFunctions
    ),
    Blanket.action: BlanketMapping(
        u"logic.action", u"get_actions", p.IActions
    ),
    Blanket.blueprint: BlanketMapping(
        u"views", u"get_blueprint", p.IBlueprint
    ),
    Blanket.cli: BlanketMapping(u"cli", u"get_commands", p.IClick),
    Blanket.validator: BlanketMapping(
        u"logic.validators", u"get_validators", p.IValidators
    ),
}


def _as_implementation(subject: Subject, as_list: bool) -> Callable[..., Any]:
    """Convert subject into acceptable interface implementation.

    Subject is one of:
    * function - used as implementation;
    * module - implementation will provide all exportable items from it;
    * dict/list - implementation will return subject as is;
    """

    def func(
        self: p.SingletonPlugin, *args: Any, **kwargs: Any
    ) -> Union[Dict[str, Any], List[Any]]:
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


def _blanket_implementation(
    group: Blanket,
) -> Callable[[Optional[Subject]], Callable[..., Any]]:
    """Generator of blanket types.

    Unless blanket requires something fancy, this function should be
    used in order to obtain new blanket type. Provide simple version:
    `oneInterface-oneMethod-oneImportPath`.

    """

    def decorator(subject: Optional[Subject] = None) -> Callable[..., Any]:
        def wrapper(plugin: Type[p.SingletonPlugin]):
            class wrapped_plugin(plugin):
                for key in Blanket:
                    if key is Blanket._all:
                        continue
                    if key & group:
                        p.implements(key.interface())
                        key.implement(locals(), plugin, subject)

            return update_wrapper(wrapped_plugin, plugin, updated=[])

        if isinstance(subject, type) and issubclass(
            subject, p.SingletonPlugin
        ):
            plugin = subject
            subject = None
            return wrapper(plugin)
        return wrapper

    return decorator


_everything = _blanket_implementation(Blanket._all)
helper = _blanket_implementation(Blanket.helper)
auth = _blanket_implementation(Blanket.auth)
action = _blanket_implementation(Blanket.action)
blueprint = _blanket_implementation(Blanket.blueprint)
cli = _blanket_implementation(Blanket.cli)
validator = _blanket_implementation(Blanket.validator)
