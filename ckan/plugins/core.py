# encoding: utf-8

'''
Provides plugin services to the CKAN
'''
from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from typing import (Any, Generic, Iterator, TypeVar, Union)
from typing_extensions import TypeGuard
from pkg_resources import iter_entry_points


from ckan.common import config
from ckan.types import SignalMapping

from . import interfaces
from .base import Interface, Plugin, SingletonPlugin, PluginNotFoundException


__all__ = [
    'PluginImplementations', 'implements',
    'PluginNotFoundException', 'Plugin', 'SingletonPlugin',
    'load', 'load_all', 'unload', 'unload_all',
    'get_plugin', 'plugins_update',
    'use_plugin', 'plugin_loaded',
    'unload_non_system_plugins',
]

TInterface = TypeVar('TInterface', bound="Interface")

log = logging.getLogger(__name__)

# Entry point group.
PLUGINS_ENTRY_POINT_GROUP = 'ckan.plugins'

# Entry point group for system plugins (those that are part of core ckan and
# do not need to be explicitly enabled by the user)
SYSTEM_PLUGINS_ENTRY_POINT_GROUP = 'ckan.system_plugins'

# Entry point for test plugins.
TEST_PLUGINS_ENTRY_POINT_GROUP = 'ckan.test_plugins'

GROUPS = [
    PLUGINS_ENTRY_POINT_GROUP,
    SYSTEM_PLUGINS_ENTRY_POINT_GROUP,
    TEST_PLUGINS_ENTRY_POINT_GROUP,
]
# These lists are used to ensure that the correct extensions are enabled.
_PLUGINS: list[str] = []
_PLUGINS_CLASS: list[type[Plugin]] = []

# To aid retrieving extensions by name
_PLUGINS_SERVICE: dict[str, Plugin] = {}


def implements(interface: type[Interface], inherit: bool = False):
    """Can be used in the class definition of `Plugin` subclasses to
    declare the extension points that are implemented by this
    interface class.
    """
    frame = sys._getframe(1)
    locals_ = frame.f_locals
    locals_.setdefault("_implements", set()).add(interface)
    if inherit:
        locals_.setdefault("_inherited_interfaces", set()).add(interface)


def implemented_by(service: Plugin, interface: type[TInterface]) -> TypeGuard[TInterface]:
    return interface.provided_by(service)


@contextmanager
def use_plugin(
    *plugins: str
) -> Iterator[Plugin | list[Plugin]]:
    '''Load plugin(s) for testing purposes

    e.g.
    ```
    import ckan.plugins as p
    with p.use_plugin('my_plugin') as my_plugin:
        # run tests with plugin loaded
    ```
    '''

    p = load(*plugins)
    try:
        yield p
    finally:
        unload(*plugins)


class PluginImplementations(Generic[TInterface]):
    def __init__(self, interface: type[TInterface]):
        self.interface = interface

    def extensions(self):
        return [p for p in _PLUGINS_SERVICE.values() if self.interface.implemented_by(type(p))]

    def __iter__(self) -> Iterator[TInterface]:
        plugin_lookup = {pf.name: pf for pf in self.extensions()}
        plugins = config.get("ckan.plugins", [])
        if isinstance(plugins, str):
            # this happens when core declarations loaded and validated
            plugins = plugins.split()

        plugins_in_config = plugins + find_system_plugins()

        ordered_plugins = []
        for pc in plugins_in_config:
            if pc in plugin_lookup:
                ordered_plugins.append(plugin_lookup[pc])
                plugin_lookup.pop(pc)

        if plugin_lookup:
            # Any oustanding plugin not in the ini file (ie system ones),
            # add to the end of the iterator
            ordered_plugins.extend(plugin_lookup.values())

        if self.interface._reverse_iteration_order:
            ordered_plugins = list(reversed(ordered_plugins))

        return iter(ordered_plugins)



def get_plugin(plugin: str) -> Plugin | None:
    ''' Get an instance of a active plugin by name.  This is helpful for
    testing. '''
    if plugin in _PLUGINS_SERVICE:
        return _PLUGINS_SERVICE[plugin]
    return None


def plugins_update() -> None:
    ''' This is run when plugins have been loaded or unloaded and allows us
    to run any specific code to ensure that the new plugin setting are
    correctly setup '''
    import ckan.config.environment as environment
    environment.update_config()


def load_all() -> None:
    '''
    Load all plugins listed in the 'ckan.plugins' config directive.
    '''
    # Clear any loaded plugins
    unload_all()

    plugins = config.get('ckan.plugins') + find_system_plugins()

    load(*plugins)


def load(
        *plugins: str
) -> Union[Plugin, list[Plugin]]:
    '''
    Load named plugin(s).
    '''
    output = []

    observers = PluginImplementations(interfaces.IPluginObserver)
    for plugin in plugins:
        if plugin in _PLUGINS:
            raise Exception('Plugin `%s` already loaded' % plugin)

        service = _get_service(plugin)
        for observer_plugin in observers:
            observer_plugin.before_load(service)

        _PLUGINS_SERVICE[plugin] = service

        for observer_plugin in observers:
            observer_plugin.after_load(service)

        _PLUGINS.append(plugin)
        _PLUGINS_CLASS.append(service.__class__)

        if implemented_by(service, interfaces.ISignal):
            _connect_signals(service.get_signal_subscriptions())
        output.append(service)
    plugins_update()

    # Return extension instance if only one was loaded.  If more that one
    # has been requested then a list of instances is returned in the order
    # they were asked for.
    if len(output) == 1:
        return output[0]
    return output


def unload_all() -> None:
    '''
    Unload (deactivate) all loaded plugins in the reverse order that they
    were loaded.
    '''
    unload(*reversed(_PLUGINS))


def unload(*plugins: str) -> None:
    '''
    Unload named plugin(s).
    '''
    from . import interfaces

    observers = PluginImplementations(interfaces.IPluginObserver)

    for plugin in plugins:
        if plugin in _PLUGINS:
            _PLUGINS.remove(plugin)
        else:
            raise Exception('Cannot unload plugin `%s`' % plugin)
        service = _get_service(plugin)
        _PLUGINS_CLASS.remove(service.__class__)

        if plugin in _PLUGINS_SERVICE:
            del _PLUGINS_SERVICE[plugin]

        for observer_plugin in observers:
            observer_plugin.before_unload(service)

        for observer_plugin in observers:
            observer_plugin.after_unload(service)

        if implemented_by(service, interfaces.ISignal):
            _disconnect_signals(service.get_signal_subscriptions())

    plugins_update()


def plugin_loaded(name: str) -> bool:
    '''
    See if a particular plugin is loaded.
    '''
    if name in _PLUGINS:
        return True
    return False


def find_system_plugins() -> list[str]:
    '''
    Return all plugins in the ckan.system_plugins entry point group.

    These are essential for operation and therefore cannot be
    enabled/disabled through the configuration file.
    '''

    eps = []
    for ep in iter_entry_points(group=SYSTEM_PLUGINS_ENTRY_POINT_GROUP):
        ep.load()
        eps.append(ep.name)
    return eps


def unload_non_system_plugins():
    """Unload all plugins except for system plugins.

    System plugins must remain available because they provide essential CKAN
    functionality.

    At the moment we have only one system plugin - synchronous_search - which
    automatically sends all datasets to Solr after modifications. Without it
    you have to indexed datasets manually after any `package_*` action.

    """
    system_plugins = find_system_plugins()
    plugins_to_unload = [
        p for p in reversed(_PLUGINS)
        if p not in system_plugins
    ]
    unload(*plugins_to_unload)


def _get_service(plugin_name: Union[str, Any]) -> Plugin:
    '''
    Return a service (ie an instance of a plugin class).

    :param plugin_name: the name of a plugin entry point
    :type plugin_name: string

    :return: the service object
    '''

    if isinstance(plugin_name, str):
        for group in GROUPS:
            iterator = iter_entry_points(
                group=group,
                name=plugin_name
            )
            plugin = next(iterator, None)
            if plugin:
                return plugin.load()(name=plugin_name)
        raise PluginNotFoundException(plugin_name)
    else:
        raise TypeError('Expected a plugin name', plugin_name)


def _connect_signals(mapping: SignalMapping):
    for signal, listeners in mapping.items():
        for options in listeners:
            if not isinstance(options, dict):
                options = {'receiver': options}
            signal.connect(**options)


def _disconnect_signals(mapping: SignalMapping):
    for signal, listeners in mapping.items():
        for options in listeners:
            if isinstance(options, dict):
                options.pop('weak', None)
            else:
                options = {'receiver': options}
            signal.disconnect(**options)
