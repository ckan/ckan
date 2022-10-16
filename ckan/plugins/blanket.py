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
implement and the default source where the blanket will automatically look for
items to import:

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Decorator
     - Interfaces
     - Default source
   * - ``toolkit.blanket.helpers``
     - :py:class:`~ckan.plugins.interfaces.ITemplateHelpers`
     - ``ckanext.myext.helpers``

   * - ``toolkit.blanket.auth_functions``
     - :py:class:`~ckan.plugins.interfaces.IAuthFunctions`
     - ``ckanext.myext.logic.auth``

   * - ``toolkit.blanket.actions``
     - :py:class:`~ckan.plugins.interfaces.IActions`
     - ``ckanext.myext.logic.action``

   * - ``toolkit.blanket.validators``
     - :py:class:`~ckan.plugins.interfaces.IValidators`
     - ``ckanext.myext.logic.validators``

   * - ``toolkit.blanket.blueprints``
     - :py:class:`~ckan.plugins.interfaces.IBlueprint`
     - ``ckanext.myext.logic.views``

   * - ``toolkit.blanket.cli``
     - :py:class:`~ckan.plugins.interfaces.IClick`
     - ``ckanext.myext.cli``

   * - ``toolkit.blanket.config_declarations``
     - :py:class:`~ckan.plugins.interfaces.IConfigDeclaration`
     - ``ckanext/myext/config_declaration.{json,yaml,toml}``


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

.. note:: The ``config_declarations`` blanket is an exception. Instead of a
          module object it accepts path to the JSON, YAML or TOML file with the
          config declarations.

You can also pass a function that produces the artifacts required by the
interface::

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

from __future__ import annotations

import logging
import enum
import types
import inspect
import pathlib
import json
import yaml

from importlib import import_module
from typing import (
    Any, Callable, NamedTuple, Optional, Type, Union, Dict, overload
)

import flask

import ckan.plugins as p
from ckan.authz import get_local_functions

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

PluginSubject = Type[p.SingletonPlugin]
SimpleSubject = Union[types.ModuleType, "dict[str, Any]", "list[Any]", str]
SubjectFactory = Callable[..., Any]

Subject = Union[PluginSubject, SimpleSubject, SubjectFactory]
ModuleHarvester = Callable[[types.ModuleType], "dict[str, Any]"]


class Blanket(enum.Flag):
    """Enumeration of all available blanket types."""

    helpers = enum.auto()
    auth_functions = enum.auto()
    actions = enum.auto()
    blueprints = enum.auto()
    cli = enum.auto()
    validators = enum.auto()
    config_declarations = enum.auto()

    def get_subject(self, plugin: p.SingletonPlugin) -> Subject:
        """Extract artifacts required for the default implementation.

        Depending on interface, this method can produce function that satisfy
        iterface's requirements, or collection with items that are used by the
        interface, or path to the file(config_declaration).
        """
        return _mapping[self].extract_subject(plugin)

    def make_implementation(self, subject: Subject):
        """Create the actual function-implementation."""
        return _mapping[self].implementation_factory(subject)

    def method_name(self) -> str:
        """Return the name of the method, required for implementation."""
        return _mapping[self].method_name

    def interface(self) -> p.Interface:
        """Return interface provided by blanket."""
        return _mapping[self].interface

    def implement(
        self,
        plugin: p.SingletonPlugin,
        subject: Optional[Subject],
    ):
        """Implement for interface inside the given plugin."""
        if subject is None:
            subject = self.get_subject(plugin)
        setattr(plugin, self.method_name(), self.make_implementation(subject))


class Mapping(NamedTuple):
    extract_subject: Callable[[p.SingletonPlugin], Subject]
    method_name: str
    interface: p.Interface
    implementation_factory: Callable[..., Any]


def _module_extractor(path: str):
    """Import sub-modue of the plugin."""

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


def _declaration_file_extractor(plugin: p.SingletonPlugin):
    """Compute the path to a file that contains config declarations."""
    path = _plugin_root(plugin)
    options = list(path.glob("config_declaration.*"))
    if not options:
        log.error(
            "Unable to import config_declaration for "
            "blanket implementation of %s",
            plugin.__name__,
        )
        raise FileNotFoundError("config_declaration.EXT")

    if len(options) > 1:
        log.error("Found multiple declaration files for %s", plugin.__name__)
        raise ValueError(options)

    return str(options[0])


def _plugin_root(plugin: p.SingletonPlugin) -> pathlib.Path:
    """Return the path to the plugin's root(`ckanext/ext`)."""
    root = plugin.__module__.rsplit(".", 1)[0]
    file_ = inspect.getsourcefile(import_module(root))
    if not file_:
        log.error("Cannot locate source file for %s", plugin)
        raise ValueError(plugin)
    return pathlib.Path(file_).parent.resolve()


def _dict_implementation(subject: Subject) -> Callable[..., dict[str, Any]]:
    return _as_implementation(subject, False, _get_public_members)


def _list_implementation(subject: Subject) -> Callable[..., list[Any]]:
    return _as_implementation(subject, True, _get_public_members)


def _blueprint_implementation(
    subject: Subject,
) -> Callable[..., list[flask.Blueprint]]:
    return _as_implementation(subject, True, _get_blueprint_members)


def _as_implementation(
    subject: Subject, as_list: bool, harvester: ModuleHarvester
) -> Callable[..., Any]:
    """Convert subject into acceptable interface implementation.

    Subject is one of:
    * function - used as implementation;
    * module - implementation will provide all exportable items from it;
    * dict/list - implementation will return subject as is;
    """

    def func(
        self: p.SingletonPlugin, *args: Any, **kwargs: Any
    ) -> Union[dict[str, Any], list[Any]]:
        if callable(subject):
            return subject(*args, **kwargs)
        elif isinstance(subject, types.ModuleType):
            result = harvester(subject)
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


def _declaration_implementation(subject: Subject) -> Callable[..., None]:
    loaders = {
        ".json": json.load,
        ".yaml": yaml.safe_load,
        ".yml": yaml.safe_load,
    }
    try:
        import toml
        loaders[".toml"] = toml.load
    except ImportError:
        pass

    def func(plugin: p.SingletonPlugin, declaration: Any, key: Any):
        if isinstance(subject, types.FunctionType):
            return subject(declaration, key)
        elif isinstance(subject, dict):
            return declaration.load_dict(subject)
        elif isinstance(subject, str):
            source = pathlib.Path(subject)
            if not source.is_absolute():
                source = _plugin_root(plugin) / subject

            if not source.is_file():
                raise ValueError("%s is not a file", source)

            data_dict = loaders[source.suffix.lower()](source.open("rb"))

            return declaration.load_dict(data_dict)

        else:
            raise TypeError(
                "Unsupported subject for config declaration of "
                f"{plugin.__name__}: {type(subject)}"
            )

    return func


_mapping: Dict[Blanket, Mapping] = {
    Blanket.helpers: Mapping(
        _module_extractor("helpers"),
        "get_helpers",
        p.ITemplateHelpers,
        _dict_implementation,
    ),
    Blanket.auth_functions: Mapping(
        _module_extractor("logic.auth"),
        "get_auth_functions",
        p.IAuthFunctions,
        _dict_implementation,
    ),
    Blanket.actions: Mapping(
        _module_extractor("logic.action"),
        "get_actions",
        p.IActions,
        _dict_implementation,
    ),
    Blanket.blueprints: Mapping(
        _module_extractor("views"),
        "get_blueprint",
        p.IBlueprint,
        _blueprint_implementation,
    ),
    Blanket.cli: Mapping(
        _module_extractor("cli"),
        "get_commands",
        p.IClick,
        _list_implementation,
    ),
    Blanket.validators: Mapping(
        _module_extractor("logic.validators"),
        "get_validators",
        p.IValidators,
        _dict_implementation,
    ),
    Blanket.config_declarations: Mapping(
        _declaration_file_extractor,
        "declare_config_options",
        p.IConfigDeclaration,
        _declaration_implementation,
    ),
}


def _get_explicit_members(module: types.ModuleType) -> dict[str, Any]:
    all_ = getattr(module, "__all__", [])
    return {item: getattr(module, item) for item in all_}


def _get_blueprint_members(
    module: types.ModuleType,
) -> dict[str, flask.Blueprint]:
    all_ = _get_explicit_members(module)
    if all_:
        return all_
    return dict(
        inspect.getmembers(
            module, lambda member: isinstance(member, flask.Blueprint)
        )
    )


def _get_public_members(module: types.ModuleType) -> dict[str, Any]:
    return _get_explicit_members(module) or dict(get_local_functions(module))


def _blanket_implementation(
    group: Blanket,
):
    """Generator of blanket types.

    Unless blanket requires something fancy, this function should be
    used in order to obtain new blanket type. Provide simple version:
    `oneInterface-oneMethod-oneImportPath`.

    """

    @overload
    def decorator(subject: PluginSubject) -> PluginSubject: ...

    @overload
    def decorator(
            subject: Union[SimpleSubject, SubjectFactory, None]
    ) -> types.FunctionType: ...

    def decorator(
            subject: Optional[Subject] = None
    ) -> Union[PluginSubject, Callable[[PluginSubject], PluginSubject]]:

        def wrapper(plugin: PluginSubject) -> PluginSubject:
            for key in Blanket:
                if key & group:
                    # short version of the trick performed by
                    # `ckan.plugin.implements`
                    if not hasattr(plugin, "_implements"):
                        setattr(plugin, "_implements", {})
                    plugin._implements.setdefault(key.interface(), [None])
                    plugin.__interfaces__.setdefault(key.interface(), [None])

                    key.implement(plugin, subject)
            return plugin

        if not isinstance(subject, type) or not issubclass(
                subject, p.SingletonPlugin):
            return wrapper

        plugin = subject
        subject = None
        return wrapper(plugin)

    return decorator


helpers = _blanket_implementation(Blanket.helpers)
auth_functions = _blanket_implementation(Blanket.auth_functions)
actions = _blanket_implementation(Blanket.actions)
blueprints = _blanket_implementation(Blanket.blueprints)
cli = _blanket_implementation(Blanket.cli)
validators = _blanket_implementation(Blanket.validators)
config_declarations = _blanket_implementation(Blanket.config_declarations)
