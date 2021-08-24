# -*- coding: utf-8 -*-

"""Quick implementations of simple plugin interfaces.

Blankets allow to reduce boilerplate code in plugins by simplifying the way
common interfaces are registered.

For instance, this is how template helpers are generally added using the
:py:class:`~ckan.plugins.interfaces.ITemplateHelpers` interface::

    from ckan import plugins as p
    from ckanext.myext import helpers


    class MyPlugin(p.SingletonPlugin):

        p.implements(ITemplateHelpers)

        def get_helpers(self):

            return {
                'my_ext_custom_helper_1': helpers.my_ext_custom_helper_1,
                'my_ext_custom_helper_2': helpers.my_ext_custom_helper_2,
            }

The same pattern is used for :py:class:`~ckan.plugins.interfaces.IActions`,
:py:class:`~ckan.plugins.interfaces.IAuthFunctions`, etc.

With Blankets, assuming that you have created your module in the expected path
with the expected name (see below), you can automate the registration of your
helpers using the corresponding blanket decorator from the plugins toolkit::


    @p.toolkit.blanket.helpers
    class MyPlugin(p.SingletonPlugin):
        pass


The following table lists the available blanket decorators, the interface they
implement and the default module path where the blanket will automatically look
for items to import:


+---------------------------------------+------------------------------------\
-------------------+--------------------------------+
| Decorator                             | Interface                          \
                   | Default module path            |
+=======================================+====================================\
===================+================================+
| ``toolkit.blanket.helpers``           | :py:class:`~ckan.plugins.interfaces\
.ITemplateHelpers` | ckanext.myext.helpers          |
+---------------------------------------+------------------------------------\
-------------------+--------------------------------+
| ``toolkit.blanket.auth_functions``    | :py:class:`~ckan.plugins.interfaces\
.IAuthFunctions`   | ckanext.myext.logic.auth       |
+---------------------------------------+------------------------------------\
-------------------+--------------------------------+
| ``toolkit.blanket.actions``           | :py:class:`~ckan.plugins.interfaces\
.IActions`         | ckanext.myext.logic.action     |
+---------------------------------------+------------------------------------\
-------------------+--------------------------------+
| ``toolkit.blanket.validators``        | :py:class:`~ckan.plugins.interfaces\
.IValidators`      | ckanext.myext.logic.validators |
+---------------------------------------+------------------------------------\
-------------------+--------------------------------+
| ``toolkit.blanket.blueprints``        | :py:class:`~ckan.plugins.interfaces\
.IBlueprint`       | ckanext.myext.logic.views      |
+---------------------------------------+------------------------------------\
-------------------+--------------------------------+
| ``toolkit.blanket.cli``               | :py:class:`~ckan.plugins.interfaces\
.IClick`           | ckanext.myext.cli              |
+---------------------------------------+------------------------------------\
-------------------+--------------------------------+


.. note:: By default, all local module members, whose ``__name__``/``name``
          doesn't start with an underscore are exported. If the module has
          ``__all__`` list, only members listed inside this list will be
          exported.


If your extension uses a different naming convention for your modules, it is
still possible to use blankets by passing the relevant module as a parameter to
the decorator::

    import ckanext.myext.custom_actions as custom_module

    @p.toolkit.blanket.actions(custom_module)
    class MyPlugin(p.SingletonPlugin):
        pass

You can also pass a function that returns the items required by the interface::

    def all_actions():
        return {'ext_action': ext_action}

    @p.toolkit.blanket.actions(all_actions)
    class MyPlugin(p.SingletonPlugin):
        pass

Or just a dict with the items required by the interface::

    all_actions = {'ext_action': ext_action}

    @p.toolkit.blanket.actions(all_actions)
    class MyPlugin(p.SingletonPlugin):
        pass

"""

import logging
import enum
import types
import inspect

from functools import update_wrapper
from importlib import import_module
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Type, Union

import ckan.plugins as p

__all__ = [
    "helpers",
    "auth_functions",
    "actions",
    "blueprints",
    "cli",
    "validators",
]

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

    helpers = enum.auto()
    auth_functions = enum.auto()
    actions = enum.auto()
    blueprints = enum.auto()
    cli = enum.auto()
    validators = enum.auto()

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
        return bool(self & (Blanket.cli | Blanket.blueprints))

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
    Blanket.helpers: BlanketMapping(
        u"helpers", u"get_helpers", p.ITemplateHelpers
    ),
    Blanket.auth_functions: BlanketMapping(
        u"logic.auth", u"get_auth_functions", p.IAuthFunctions
    ),
    Blanket.actions: BlanketMapping(
        u"logic.action", u"get_actions", p.IActions
    ),
    Blanket.blueprints: BlanketMapping(
        u"views", u"get_blueprint", p.IBlueprint
    ),
    Blanket.cli: BlanketMapping(u"cli", u"get_commands", p.IClick),
    Blanket.validators: BlanketMapping(
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
            result = _get_public_module_members(subject)
            if as_list:
                return list(result.values())
            return result
        else:
            return subject

    return func


def _get_public_module_members(module: types.ModuleType) -> Dict[str, Any]:
    all_ = getattr(module, u"__all__", None)
    if all_:
        return {item: getattr(module, item) for item in all_}

    def _is_public(member: Any) -> bool:
        if inspect.getmodule(member) is not module:
            return False

        name = getattr(member, "__name__", None)
        if not name:
            name = getattr(member, "name", "_")
        return not name.startswith("_")

    return dict(inspect.getmembers(module, _is_public))


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


helpers = _blanket_implementation(Blanket.helpers)
auth_functions = _blanket_implementation(Blanket.auth_functions)
actions = _blanket_implementation(Blanket.actions)
blueprints = _blanket_implementation(Blanket.blueprints)
cli = _blanket_implementation(Blanket.cli)
validators = _blanket_implementation(Blanket.validators)
