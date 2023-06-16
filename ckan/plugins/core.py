# encoding: utf-8

'''
Provides plugin services to the CKAN
'''
from __future__ import annotations

import logging
import warnings
from contextlib import contextmanager
from typing import (Any, Generic, Iterator, Optional,
                    Type, TypeVar, Union)
from pkg_resources import iter_entry_points

from pyutilib.component.core import PluginGlobals, implements
from pyutilib.component.core import ExtensionPoint
from pyutilib.component.core import SingletonPlugin as _pca_SingletonPlugin
from pyutilib.component.core import Plugin as _pca_Plugin


import ckan.plugins.interfaces as interfaces

from ckan.common import config
from ckan.types import SignalMapping
from ckan.exceptions import CkanDeprecationWarning


__all__ = [
    'PluginImplementations', 'implements',
    'PluginNotFoundException', 'Plugin', 'SingletonPlugin',
    'load', 'load_all', 'unload', 'unload_all',
    'get_plugin', 'plugins_update',
    'use_plugin', 'plugin_loaded',
]

TInterface = TypeVar('TInterface', bound=interfaces.Interface)

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
_PLUGINS_CLASS: list[Type["SingletonPlugin"]] = []

# To aid retrieving extensions by name
_PLUGINS_SERVICE: dict[str, "SingletonPlugin"] = {}


@contextmanager
def use_plugin(
    *plugins: str
) -> Iterator[Union['SingletonPlugin', list['SingletonPlugin']]]:
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


class PluginImplementations(ExtensionPoint, Generic[TInterface]):
    def __init__(self, interface: Type[TInterface], *args: Any):
        super().__init__(interface, *args)

    def __iter__(self) -> Iterator[TInterface]:
        '''
        When we upgraded pyutilib on CKAN 2.9 the order in which
        plugins were returned by `PluginImplementations` changed
        so we use this wrapper to maintain the previous order
        (which is the same as the ckan.plugins config option)
        '''

        iterator = super(PluginImplementations, self).__iter__()

        plugin_lookup = {pf.name: pf for pf in iterator}

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

        return iter(ordered_plugins)


class PluginNotFoundException(Exception):
    '''
    Raised when a requested plugin cannot be found.
    '''


class Plugin(_pca_Plugin):
    '''
    Base class for plugins which require multiple instances.

    Unless you need multiple instances of your plugin object you should
    probably use SingletonPlugin.
    '''


class SingletonPlugin(_pca_SingletonPlugin):
    '''
    Base class for plugins which are singletons (ie most of them)

    One singleton instance of this class will be created when the plugin is
    loaded. Subsequent calls to the class constructor will always return the
    same singleton instance.
    '''
    def __init__(self, *args: Any, **kwargs: Any):
        # Drop support by removing this __init__ function
        super().__init__(*args, **kwargs)

        if interfaces.IPackageController.implemented_by(type(self)):
            for old_name, new_name in [
                ["after_create", "after_dataset_create"],
                ["after_update", "after_dataset_update"],
                ["after_delete", "after_dataset_delete"],
                ["after_show", "after_dataset_show"],
                ["before_search", "before_dataset_search"],
                ["after_search", "after_dataset_search"],
                ["before_index", "before_dataset_index"],
                    ["before_view", "before_dataset_view"]]:
                if hasattr(self, old_name) and not hasattr(self, new_name):
                    msg = (
                        f"The method 'IPackageController.{old_name}' is "
                        + f"deprecated. Please use '{new_name}' instead!"
                    )
                    log.warning(msg)
                    warnings.warn(msg, CkanDeprecationWarning)
                    setattr(self, new_name, getattr(self, old_name))

        if interfaces.IResourceController.implemented_by(type(self)):
            for old_name, new_name in [
                ["before_create", "before_resource_create"],
                ["after_create", "after_resource_create"],
                ["before_update", "before_resource_update"],
                ["after_update", "after_resource_update"],
                ["before_delete", "before_resource_delete"],
                ["after_delete", "after_resource_delete"],
                    ["before_show", "before_resource_show"]]:
                if hasattr(self, old_name) and not hasattr(self, new_name):
                    msg = (
                        f"The method 'IResourceController.{old_name}' is "
                        + f"deprecated. Please use '{new_name}' instead!"
                    )
                    log.warning(msg)
                    warnings.warn(msg, CkanDeprecationWarning)
                    setattr(self, new_name, getattr(self, old_name))


def get_plugin(plugin: str) -> Optional[SingletonPlugin]:
    ''' Get an instance of a active plugin by name.  This is helpful for
    testing. '''
    if plugin in _PLUGINS_SERVICE:
        return _PLUGINS_SERVICE[plugin]
    return None


def plugins_update() -> None:
    ''' This is run when plugins have been loaded or unloaded and allows us
    to run any specific code to ensure that the new plugin setting are
    correctly setup '''

    # It is posible for extra SingletonPlugin extensions to be activated if
    # the file containing them is imported, for example if two or more
    # extensions are defined in the same file.  Therefore we do a sanity
    # check and disable any that should not be active.
    for env in PluginGlobals.env.values():
        for service, id_ in env.singleton_services.items():
            if service not in _PLUGINS_CLASS:
                PluginGlobals.plugin_instances[id_].deactivate()

    # Reset CKAN to reflect the currently enabled extensions.
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
) -> Union[SingletonPlugin, list[SingletonPlugin]]:
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
        service.activate()
        for observer_plugin in observers:
            observer_plugin.after_load(service)

        _PLUGINS.append(plugin)
        _PLUGINS_CLASS.append(service.__class__)

        if isinstance(service, SingletonPlugin):
            _PLUGINS_SERVICE[plugin] = service
        if interfaces.ISignal.implemented_by(service.__class__):
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

    observers = PluginImplementations(interfaces.IPluginObserver)

    for plugin in plugins:
        if plugin in _PLUGINS:
            _PLUGINS.remove(plugin)
            if plugin in _PLUGINS_SERVICE:
                del _PLUGINS_SERVICE[plugin]
        else:
            raise Exception('Cannot unload plugin `%s`' % plugin)

        service = _get_service(plugin)

        if interfaces.ISignal.implemented_by(service.__class__):
            _disconnect_signals(service.get_signal_subscriptions())

        for observer_plugin in observers:
            observer_plugin.before_unload(service)

        service.deactivate()

        _PLUGINS_CLASS.remove(service.__class__)

        for observer_plugin in observers:
            observer_plugin.after_unload(service)
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


def _get_service(plugin_name: Union[str, Any]) -> SingletonPlugin:
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
