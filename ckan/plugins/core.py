'''
Provides plugin services to the CKAN
'''

from contextlib import contextmanager
import logging
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
    'get_plugin', 'plugins_update',
    'use_plugin', 'plugin_loaded',
]

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
_PLUGINS = []
_PLUGINS_CLASS = []

# To aid retrieving extensions by name
_PLUGINS_SERVICE = {}


@contextmanager
def use_plugin(*plugins):
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


def get_plugin(plugin):
    ''' Get an instance of a active plugin by name.  This is helpful for
    testing. '''
    if plugin in _PLUGINS_SERVICE:
        return _PLUGINS_SERVICE[plugin]


def plugins_update():
    ''' This is run when plugins have been loaded or unloaded and allows us
    to run any specific code to ensure that the new plugin setting are
    correctly setup '''

    # It is posible for extra SingletonPlugin extensions to be activated if
    # the file containing them is imported, for example if two or more
    # extensions are defined in the same file.  Therefore we do a sanity
    # check and disable any that should not be active.
    for env in PluginGlobals.env_registry.values():
        for service in env.services.copy():
            if service.__class__ not in _PLUGINS_CLASS:
                service.deactivate()

    # Reset CKAN to reflect the currently enabled extensions.
    import ckan.config.environment as environment
    environment.update_config()


def load_all(config):
    '''
    Load all plugins listed in the 'ckan.plugins' config directive.
    '''
    # Clear any loaded plugins
    unload_all()

    plugins = config.get('ckan.plugins', '').split() + find_system_plugins()
    # Add the synchronous search plugin, unless already loaded or
    # explicitly disabled
    if 'synchronous_search' not in plugins and \
            asbool(config.get('ckan.search.automatic_indexing', True)):
        log.debug('Loading the synchronous search plugin')
        plugins.append('synchronous_search')

    load(*plugins)


def load(*plugins):
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

        if interfaces.IGenshiStreamFilter in service.__interfaces__:
            log.warn("Plugin '%s' is using deprecated interface "
                     'IGenshiStreamFilter' % plugin)

        _PLUGINS.append(plugin)
        _PLUGINS_CLASS.append(service.__class__)

        if isinstance(service, SingletonPlugin):
            _PLUGINS_SERVICE[plugin] = service

        output.append(service)
    plugins_update()

    # Return extension instance if only one was loaded.  If more that one
    # has been requested then a list of instances is returned in the order
    # they were asked for.
    if len(output) == 1:
        return output[0]
    return output


def unload_all():
    '''
    Unload (deactivate) all loaded plugins in the reverse order that they
    were loaded.
    '''
    unload(*reversed(_PLUGINS))


def unload(*plugins):
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
        for observer_plugin in observers:
            observer_plugin.before_unload(service)

        service.deactivate()

        _PLUGINS_CLASS.remove(service.__class__)

        for observer_plugin in observers:
            observer_plugin.after_unload(service)
    plugins_update()


def plugin_loaded(name):
    '''
    See if a particular plugin is loaded.
    '''
    if name in _PLUGINS:
        return True
    return False


def find_system_plugins():
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


def _get_service(plugin_name):
    '''
    Return a service (ie an instance of a plugin class).

    :param plugin_name: the name of a plugin entry point
    :type plugin_name: string

    :return: the service object
    '''

    if isinstance(plugin_name, basestring):
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
