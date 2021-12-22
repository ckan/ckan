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

from __future__ import annotations

import logging
import enum
import types
import inspect
import pathlib

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
    "config_declarations",
]

log = logging.getLogger(__name__)

Subject = Union[
    types.FunctionType, types.ModuleType, Dict[str, Any], List[Any], str
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
    config_declarations = enum.auto()

    def get_subject(self, plugin: p.SingletonPlugin) -> Subject:
        return _mapping[self].source(plugin)

    def make_implementation(self, subject: Subject):
        return _mapping[self].implementation_factory(subject)

    def method(self) -> str:
        """Return the name of the method, required for implementation."""
        return _mapping[self].method

    def interface(self) -> p.Interface:
        """Return interface provided by blanket."""
        return _mapping[self].interface

    def implement(
        self,
        locals: Dict[str, Any],
        plugin: p.SingletonPlugin,
        subject: Optional[Subject],
    ):
        """Provide implementation for interface."""
        if subject is None:
            subject = self.get_subject(plugin)
        locals[self.method()] = self.make_implementation(subject)


class BlanketMapping(NamedTuple):
    source: Callable[[p.SingletonPlugin], Subject]
    method: str
    interface: p.Interface
    implementation_factory: Callable[..., Any]


def _plugin_source(path: str):
    def source(plugin: p.SingletonPlugin):
        root = plugin.__module__.rsplit(".", 1)[0]
        import_path = ".".join([root, path])
        try:
            return import_module(import_path)
        except ImportError:
            log.error(
                "Unable to import <%s> for blanket implementation of %s",
                import_path,
                plugin.__name__,
            )
            raise

    return source


def _declaration_source(plugin: p.SingletonPlugin):
    root = plugin.__module__.rsplit(".", 1)[0]
    module = import_module(root)
    module_path = module.__file__
    if not module_path:
        log.error("Cannot locate source file for %s", plugin)
        raise ValueError(plugin)

    options = list(
        pathlib.Path(module_path).parent.glob("config_declaration.*")
    )
    if not options:
        log.error(
            "Unable to import config_declaration for "
            "blanket implementation of %s",
            "config_declaration",
            plugin.__name__,
        )
        raise FileNotFoundError("config_declaration.EXT")
    if len(options) > 1:
        log.warning(
            "Found multiple declaration files for %s, using first match: %s",
            plugin.__name__,
            options,
        )
    return str(options[0])


def _dict_implementation(subject: Subject) -> Callable[..., dict[str, Any]]:
    return _as_implementation(subject, False)


def _list_implementation(subject: Subject) -> Callable[..., list[Any]]:
    return _as_implementation(subject, True)


def _declaration_implementation(subject: Subject) -> Callable[..., None]:
    def func(self: p.SingletonPlugin, declaration: Any, key: Any) -> None:
        if isinstance(subject, types.FunctionType):
            return subject(declaration, key)
        elif isinstance(subject, dict):
            return declaration.load_dict(subject)
        elif isinstance(subject, str):
            # TODO: implement
            ...
        else:
            raise TypeError(
                "Unsupported subject for config declaration of "
                f"{self.__name__}: {type(subject)}"
            )

    return func


_mapping: Dict[Blanket, BlanketMapping] = {
    Blanket.helpers: BlanketMapping(
        _plugin_source("helpers"),
        "get_helpers",
        p.ITemplateHelpers,
        _dict_implementation,
    ),
    Blanket.auth_functions: BlanketMapping(
        _plugin_source("logic.auth"),
        "get_auth_functions",
        p.IAuthFunctions,
        _dict_implementation,
    ),
    Blanket.actions: BlanketMapping(
        _plugin_source("logic.action"),
        "get_actions",
        p.IActions,
        _dict_implementation,
    ),
    Blanket.blueprints: BlanketMapping(
        _plugin_source("views"),
        "get_blueprint",
        p.IBlueprint,
        _list_implementation,
    ),
    Blanket.cli: BlanketMapping(
        _plugin_source("cli"), "get_commands", p.IClick, _list_implementation
    ),
    Blanket.validators: BlanketMapping(
        _plugin_source("logic.validators"),
        "get_validators",
        p.IValidators,
        _dict_implementation,
    ),
    Blanket.config_declarations: BlanketMapping(
        _declaration_source,
        "declare_config_options",
        p.IConfigDeclaration,
        _declaration_implementation,
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
        elif isinstance(subject, str):
            raise TypeError(
                "Unsupported str-subject inside blanket implementation for "
                f"{self.__name__}"
            )
        else:
            return subject

    return func


def _get_public_module_members(module: types.ModuleType) -> Dict[str, Any]:
    all_ = getattr(module, "__all__", None)
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
            class WrappedPlugin(plugin):
                for key in Blanket:
                    if key & group:
                        p.implements(key.interface())
                        key.implement(locals(), plugin, subject)

            return update_wrapper(WrappedPlugin, plugin, updated=[])

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
config_declarations = _blanket_implementation(Blanket.config_declarations)
