"""
Provides plugin services to the CKAN
"""

import logging
from inspect import isclass
from itertools import chain

from pkg_resources import iter_entry_points
from pyutilib.component.core import PluginGlobals, implements
from pyutilib.component.core import ExtensionPoint as PluginImplementations
from pyutilib.component.core import SingletonPlugin as _pca_SingletonPlugin
from pyutilib.component.core import Plugin as _pca_Plugin
from paste.deploy.converters import asbool

import interfaces

__all__ = [
    'PluginImplementations', 'implements',
    'PluginNotFoundException', 'Plugin', 'SingletonPlugin',
    'load', 'load_all', 'unload', 'unload_all',
    'reset', 'get_pugin',
]

log = logging.getLogger(__name__)

# Entry point group.
PLUGINS_ENTRY_POINT_GROUP = "ckan.plugins"

# Entry point group for system plugins (those that are part of core ckan and do
# not need to be explicitly enabled by the user)
SYSTEM_PLUGINS_ENTRY_POINT_GROUP = "ckan.system_plugins"

_plugins = {}

class PluginNotFoundException(Exception):
    """
    Raised when a requested plugin cannot be found.
    """


class Plugin(_pca_Plugin):
    """
    Base class for plugins which require multiple instances.

    Unless you need multiple instances of your plugin object you should
    probably use SingletonPlugin.
    """


class SingletonPlugin(_pca_SingletonPlugin):
    """
    Base class for plugins which are singletons (ie most of them)

    One singleton instance of this class will be created when the plugin is
    loaded. Subsequent calls to the class constructor will always return the
    same singleton instance.
    """


def _get_service(plugin):
    """
    Return a service (ie an instance of a plugin class).

    :param plugin: any of: the name of a plugin entry point; a plugin class; an
        instantiated plugin object.
    :return: the service object
    """

    if isinstance(plugin, basestring):
        try:
            name = plugin
            (plugin,) = iter_entry_points(
                group=PLUGINS_ENTRY_POINT_GROUP,
                name=name
            )
        except ValueError:
            raise PluginNotFoundException(plugin)

        return plugin.load()(name=name)

##    elif isinstance(plugin, _pca_Plugin):
##        return plugin
##
##    elif isclass(plugin) and issubclass(plugin, _pca_Plugin):
##        return plugin()

    else:
        raise TypeError("Expected a plugin name, class or instance", plugin)


def get_pugin(plugin):
    return _plugins[plugin]


def load_all(config):
    """
    Load all plugins listed in the 'ckan.plugins' config directive.
    """
  ##  plugins = chain(
  ##      find_system_plugins(),
  ##      find_user_plugins(config)
  ##  )


    # PCA default behaviour is to activate SingletonPlugins at import time. We
    # only want to activate those listed in the config, so clear
    # everything then activate only those we want.
    unload_all(update=False)

   ## for plugin in plugins:
    for plugin in config.get('ckan.plugins', '').split():
        load(plugin, update=False)

    # Load the synchronous search plugin, unless already loaded or
    # explicitly disabled
    if not 'synchronous_search' in config.get('ckan.plugins',[]) and \
            asbool(config.get('ckan.search.automatic_indexing', True)):
        log.debug('Loading the synchronous search plugin')
        load('synchronous_search', update=False)

    plugins_update()


def reset():
    """
    Clear and reload all configured plugins
    """
    # FIXME This looks like it should be removed
    from pylons import config
    load_all(config)


def plugins_update():
    ''' This is run when plugins have been loaded or unloaded and allows us
    to run any specific code to ensure that the new plugin setting are
    correctly setup '''
    import ckan.config.environment as environment
    environment.update_config()


def load(plugin, update=True):
    """
    Load a single plugin, given a plugin name, class or instance
    """
    observers = PluginImplementations(interfaces.IPluginObserver)
    for observer_plugin in observers:
        observer_plugin.before_load(plugin)
    service = _get_service(plugin)
    service.activate()
    for observer_plugin in observers:
        observer_plugin.after_load(service)

    if interfaces.IGenshiStreamFilter in service.__interfaces__:
       log.warn("Plugin '%s' is using deprecated interface IGenshiStreamFilter" % plugin)

    if update:
        plugins_update()

    _plugins[plugin] = service

    return service


def unload_all(update=True):
    """
    Unload (deactivate) all loaded plugins
    """
  ##  for env in PluginGlobals.env_registry.values():
  ##      for service in env.services.copy():
  ##          unload(service, update=False)

    # We copy the _plugins dict so we can delete entries
    for plugin in _plugins.copy():
        unload(plugin, update=False)

    if update:
        plugins_update()


def unload(plugin, update=True):
    """
    Unload a single plugin, given a plugin name, class or instance
    """
    observers = PluginImplementations(interfaces.IPluginObserver)
    service = _get_service(plugin)
    for observer_plugin in observers:
        observer_plugin.before_unload(service)

    service.deactivate()

    for observer_plugin in observers:
        observer_plugin.after_unload(service)

    del _plugins[plugin]
    if update:
        plugins_update()

    return service


##def find_user_plugins(config):
##    """
##    Return all plugins specified by the user in the 'ckan.plugins' config
##    directive.
##    """
##    plugins = []
##    for name in config.get('ckan.plugins', '').split():
##        entry_points = list(
##            iter_entry_points(group=PLUGINS_ENTRY_POINT_GROUP, name=name)
##        )
##        if not entry_points:
##            raise PluginNotFoundException(name)
##        plugins.extend(ep.load() for ep in entry_points)
##    return plugins
##
##
##def find_system_plugins():
##    """
##    Return all plugins in the ckan.system_plugins entry point group.
##
##    These are essential for operation and therefore cannot be enabled/disabled
##    through the configuration file.
##    """
##    return (
##        ep.load()
##        for ep in iter_entry_points(group=SYSTEM_PLUGINS_ENTRY_POINT_GROUP)
##    )
