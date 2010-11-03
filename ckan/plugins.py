"""
Provides plugin services to the CKAN
"""

import logging
from itertools import chain
from pkg_resources import iter_entry_points
from pyutilib.component.core import Interface, PluginGlobals, ExtensionPoint, implements
from pyutilib.component.core import SingletonPlugin as _pca_SingletonPlugin
from pyutilib.component.core import Plugin as _pca_Plugin
from pyutilib.component.core import PluginEnvironment
from sqlalchemy.orm.interfaces import MapperExtension

__all__ = [
    'ExtensionPoint', 'implements',
    'Plugin', 'SingletonPlugin',
    'IRenderFilterer', 'IRoutesMapExtension', 'IMapperExtension',
    'IDomainObjectNotification'
]

log = logging.getLogger(__name__)

# Entry point group. 
PLUGINS_ENTRY_POINT_GROUP = "ckan.plugins"

# Entry point group for system plugins (those that are part of core ckan and do
# not need to be explicitly enabled by the user)
SYSTEM_PLUGINS_ENTRY_POINT_GROUP = "ckan.system_plugins"

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

class IGenshiStreamFilter(Interface):
    '''
    Hook into template rendering.
    See ckan.lib.base.py:render
    '''

    def filter(self, stream):
        """
        Return a filtered Genshi stream.
        Called when any page is rendered.

        :param stream: Genshi stream of the current output document
        :returns: filtered Genshi stream
        """

class IRoutesExtension(Interface):
    """
    Plugin into the setup of the routes map creation.

    """
    def before_map(self, map):
        """
        Called before the routes map is generated. ``before_map`` is before any
        other mappings are created so can override all other mappings.

        :param map: Routes map object
        :returns: Modified version of the map object
        """

    def after_map(self, map):
        """
        Called after routes map is set up. ``after_map`` can be used to add fall-back handlers. 

        :param map: Routes map object
        :returns: Modified version of the map object
        """

class IMapperExtension(Interface):
    """
    A subset of the SQLAlchemy mapper extension hooks.
    See http://www.sqlalchemy.org/docs/05/reference/orm/interfaces.html#sqlalchemy.orm.interfaces.MapperExtension

    Example::

        >>> class MyPlugin(SingletonPlugin):
        ...
        ...     implements(IMapperExtension)
        ...
        ...     def after_update(self, mapper, connection, instance):
        ...         log("Updated: %r", instance)
    """

    def before_insert(self, mapper, connection, instance):
        """
        Receive an object instance before that instance is INSERTed into its table.
        """

    def before_update(self, mapper, connection, instance):
        """
        Receive an object instance before that instance is UPDATEed.
        """

    def before_delete(self, mapper, connection, instance):
        """
        Receive an object instance before that instance is DELETEed.
        """

    def after_insert(self, mapper, connection, instance):
        """
        Receive an object instance after that instance is INSERTed.
        """
                                     
    def after_update(self, mapper, connection, instance):
        """
        Receive an object instance after that instance is UPDATEed.
        """
    
    def after_delete(self, mapper, connection, instance):
        """
        Receive an object instance after that instance is DELETEed.
        """

class ISessionExtension(Interface):
    """
    A subset of the SQLAlchemy session extension hooks.
    """

    def after_begin(self, session, transaction, connection):
        """
        Execute after a transaction is begun on a connection
        """

    def before_flush(self, session, flush_context, instances):
        """
        Execute before flush process has started.
        """

    def after_flush(self, session, flush_context):
        """
        Execute after flush has completed, but before commit has been called.
        """

    def before_commit(self, session):
        """
        Execute right before commit is called.
        """

    def after_commit(self, session):
        """
        Execute after a commit has occured.
        """

    def after_rollback(self, session):
        """
        Execute after a rollback has occured.
        """

class IDomainObjectNotification(Interface):
    """
    Receives notification of new and changed domain objects
    """

    def after_insert(self, mapper, connection, instance):
        pass

    def after_update(self, mapper, connection, instance):
        pass


def load_all(config):
    """
    Load all plugins listed in the 'ckan.plugins' config directive.
    """
    plugins = chain(
        find_system_plugins(),
        find_user_plugins(config)
    )

    # PCA default behaviour is to activate SingletonPlugins at import time. We
    # only want to activate those listed in the config, so clear
    # everything then activate only those we want.
    unload_all()

    for plugin in plugins:
        load(plugin)

def reset():
    """
    Clear and reload all configured plugins
    """
    from pylons import config
    load_all(config)

def load(plugin):
    """
    Load a single plugin
    """
    if isinstance(plugin, (SingletonPlugin, Plugin)):
        service = plugin
    elif issubclass(plugin, (SingletonPlugin, Plugin)):
        service = plugin()
    else:
        raise TypeError("Expected a plugin instance or class", plugin)
    service.activate()
    return service

def unload_all():
    """
    Unload (deactivate) all loaded plugins
    """
    for env in PluginGlobals.env_registry.values():
        for service in env.services.copy():
            service.deactivate()

def unload(plugin):
    """
    Unload a single plugin
    """
    if isinstance(plugin, (SingletonPlugin, Plugin)):
        service = plugin
    elif issubclass(plugin, (SingletonPlugin, Plugin)):
        service = plugin()
    else:
        raise TypeError("Expected a plugin instance or class", plugin)
    service.deactivate()
    return service


def find_user_plugins(config):
    """
    Return all plugins specified by the user in the 'ckan.plugins' config
    directive.
    """
    plugins = []
    for name in config.get('ckan.plugins', '').split():
        entry_points = list(
            iter_entry_points(group=PLUGINS_ENTRY_POINT_GROUP, name=name)
        )
        if not entry_points:
            raise PluginNotFoundException(name)
        plugins.extend(ep.load() for ep in entry_points)
    return plugins

def find_system_plugins():
    """
    Return all plugins in the ckan.system_plugins entry point group.
    
    These are essential for operation and therefore cannot be enabled/disabled
    through the configuration file.
    """
    return (
        ep.load()
        for ep in iter_entry_points(group=SYSTEM_PLUGINS_ENTRY_POINT_GROUP)
    )

######  Pylons monkey-patch
# Required by the deliverance plugin and iATI

from pylons.wsgiapp import PylonsApp
import pkg_resources

log.info("Monkey-patching Pylons to allow loading of controllers via entry point mechanism")

find_controller_generic = PylonsApp.find_controller

# This is from pylons 1.0 source, will monkey-patch into 0.9.7
def find_controller(self, controller):
    if controller in self.controller_classes:
        return self.controller_classes[controller]

    # Check to see if its a dotted name
    if '.' in controller or ':' in controller:
        mycontroller = pkg_resources.EntryPoint.parse('x=%s' % controller).load(False)
        self.controller_classes[controller] = mycontroller
        return mycontroller

    return find_controller_generic(self, controller)

PylonsApp.find_controller = find_controller
