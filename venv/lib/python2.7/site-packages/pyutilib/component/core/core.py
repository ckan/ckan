#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

# This software is adapted from the Trac software (specifically, the trac.core
# module.  The Trac copyright statement is included below.

"""
The PyUtilib Component Architecture (PCA) consists of the following core classes:

* Interface - Subclasses of this class declare component interfaces that are registered in the framework

* ExtensionPoint - A class used to declare extension points, which can access services with a particular interface

* Plugin - Subclasses of this class declare plugins, which can be used to provide services within the PCA.

* SingletonPlugin - Subclasses of this class declare singleton plugins, for which a single instance can be declared.

* PluginEnvironment - A class that maintains the registries for interfaces, extension points and components.

* PluginGlobals - A class that maintains global data concerning the set of environments that are currently being used.

* PluginError - The exception class that is raised when errors arise in this framework.

Note: The outline of this framework is adapted from Trac (see the trac.core module).  This framework generalizes the Trac by supporting multi-environment management of components, as well as non-singleton plugins.  For those familiar with Trac, the following classes roughly correspond with each other:

  Trac                  PyUtilib
  ----------------------------------------
  Interface             Interface
  ExtensionPoint        ExtensionPoint
  Component             SingletonPlugin
  ComponentManager      PluginEnvironment
"""

__all__ = ['Plugin', 'SingletonPlugin', 'PluginGlobals', 'PluginMeta',
           'ExtensionPoint', 'implements', 'Interface',
           'PluginError', 'PluginEnvironment', 'IPluginLoader',
           'IPluginLoadPath', 'PluginFactory', 'alias', 'CreatePluginFactory',
           'IIgnorePluginWhenLoading' ]

import re
import logging
import sys
import six

# This is a copy of the with_metaclass function from 'six' from the 
# development branch.  This fixes a bug in six 1.6.1.
# 
# Copyright (c) 2010-2014 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a
    # dummy metaclass for one level of class instantiation that replaces
    # itself with the actual metaclass.  Because of internal type checks
    # we also need to make sure that we downgrade the custom metaclass
    # for one level to something closer to type (that's why __call__ and
    # __init__ comes back from type etc.).
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__
        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass('temporary_class', None, {})


#
# Define the default logging behavior for a given namespace, which is to
# ignore the log messages.
#
def logger_factory(namespace):
    log = logging.getLogger('pyutilib.component.core.'+namespace)
    class NullHandler(logging.Handler):
        def emit(self, record):         #pragma:nocover
            """Do not generate logging record"""
    log.addHandler(NullHandler())
    return log


class PluginError(Exception):
    """Exception base class for plugin errors."""

    def __init__(self, value):
        """Constructor, whose argument is the error message"""
        self.value = value

    def __str__(self):
        """Return a string value for this message"""
        return str(self.value)


"""
Global data for plugins.  The main role of this class is to manage the stack of PluginEnvironment instances.

Note: a single ID counter is used for tagging both environment and plugins registrations.  This enables the user to track the relative order of construction of these objects.
"""
class PluginGlobals(object):

    def __init__(self):                         #pragma:nocover
        """Disable construction."""
        raise PluginError("The PluginGlobals class should not be created.")

    """The registry of interfaces, by name"""
    interface_registry = {}

    """The registry of environments, by name"""
    env_registry = {}

    """The stack of environments that is being used."""
    env_stack = []

    """A unique id used to name plugin objects"""
    id_counter = 0

    @staticmethod
    def clear(bootstrap=False):
        """
        Clears the environment stack and defines a new default environment.
        This setup is non-standard because we need to bootstrap the
        configuration of the 'pyutilib.component' environment.

        NOTE: I _think_ that the plugin_registry should also be cleared,
        but in practice that may not make sense since it's not easy to
        reload modules in Python.
        """
        PluginGlobals.clearing=True
        if len(PluginGlobals.env_stack) > 0:
            PluginGlobals.env_stack[0].log.info("Clearing the PluginGlobals data")
        PluginGlobals.env_registry = {}
        PluginGlobals.env_stack=[]
        PluginGlobals.id_counter=0
        env = PluginEnvironment(name="pca", bootstrap=True)
        PluginGlobals.env_registry[env.name] = env
        PluginGlobals.push_env( PluginEnvironment(name="<default>", bootstrap=bootstrap) )
        PluginGlobals.clearing=False

    @staticmethod
    def next_id():
        """Generate the next id for plugin objects"""
        PluginGlobals.id_counter += 1
        return PluginGlobals.id_counter

    @staticmethod
    def default_env():
        """
        Return the default environment, which is constructed when the
        plugins framework is loaded.
        """
        return PluginGlobals.env_stack[0]             #pragma:nocover

    @staticmethod
    def env(arg=None):
        """Return the current environment."""
        if arg is None:
            return PluginGlobals.env_stack[-1]
        else:
            if not arg in PluginGlobals.env_registry:
                raise PluginError("Unknown environment %r" % arg)
            return PluginGlobals.env_registry[arg]

    @staticmethod
    def push_env(arg, validate=False):
        """Push the given environment on the stack."""
        if isinstance(arg,six.string_types):
            if not arg in PluginGlobals.env_registry:
                if validate:
                    raise PluginError("Unknown environment %r" % arg)
                else:
                    env = PluginEnvironment(arg)
            env = PluginGlobals.env_registry[arg]
        else:
            env = arg
        PluginGlobals.env_stack.append(env)
        if __debug__:
            env.log.debug("Pushing environment %r on the PluginGlobals stack" % env.name)

    @staticmethod
    def pop_env():
        """Pop the current environment from the stack."""
        if len(PluginGlobals.env_stack) == 1:
            env = PluginGlobals.env_stack[0]
        else:
            env = PluginGlobals.env_stack.pop()
            if __debug__:
                env.log.debug("Popping environment %r from the PluginGlobals stack" % env.name)
        return env

    @staticmethod
    def services(name=None):
        """
        A convenience function that returns the services in the
        current environment.
        """
        return PluginGlobals.env(name).services

    @staticmethod
    def singleton_services(name=None):
        """
        A convenience function that returns the singleton
        services in the current environment.
        """
        return PluginGlobals.env(name).singleton_services

    @staticmethod
    def load_services(**kwds):
        """Load services from IPluginLoader extension points"""
        PluginGlobals.env().load_services(**kwds)

    @staticmethod
    def pprint(**kwds):
        """A pretty-print function"""
        s = ""
        s += "--------------------------------------------------------------\n"
        s += " Registered Environments\n"
        s += "--------------------------------------------------------------\n"
        keys = list(PluginGlobals.env_registry.keys())
        keys.sort()
        for key in keys:
            s += " "+key+"\n"
        s += "\n"
        s += "--------------------------------------------------------------\n"
        s += " Environment Stack\n"
        s += "--------------------------------------------------------------\n"
        i=1
        for env in PluginGlobals.env_stack:
            s += " Level="+str(i)+"  name="
            s += env.name
            s += "\n"
            i += 1
        s += "\n"
        s += "--------------------------------------------------------------\n"
        s += " Interfaces Declared\n"
        s += "--------------------------------------------------------------\n"
        keys = list(PluginGlobals.interface_registry.keys())
        keys.sort()
        for key in keys:
            s += " "+key+"\n"
        s += "\n"
        s += "--------------------------------------------------------------\n"
        s += " Interfaces Declared by Namespace\n"
        s += "--------------------------------------------------------------\n"
        keys = list(PluginGlobals.interface_registry.keys())
        keys.sort()
        tmp = {}
        for key in keys:
            tmp.setdefault(PluginGlobals.interface_registry[key].__interface_namespace__,[]).append(key)
        keys = list(tmp.keys())
        keys.sort()
        for key in keys:
            s += " "+str(key)+"\n"
            for item in tmp[key]:
                s += "     "+item+"\n"
            s += "\n"
        #
        # Coverage is disabled here because different platforms give different
        # results.
        #
        if "plugins" not in kwds or kwds["plugins"] is True:    #pragma:nocover
            s += "--------------------------------------------------------------\n"
            s += " Registered Plugins by Interface\n"
            s += "--------------------------------------------------------------\n"
            tmp = {}
            for key in PluginGlobals.interface_registry:
                tmp[PluginGlobals.interface_registry[key]] = []
            for env in PluginGlobals.env_stack:
                for key in env.plugin_registry:
                    for item in env.plugin_registry[key].__interfaces__:
                        tmp[item].append(key)
            keys = list(PluginGlobals.interface_registry.keys())
            keys.sort()
            for key in keys:
                if key == "":                   #pragma:nocover
                    s += " `"+str(key)+"`\n"
                else:
                    s += " "+str(key)+"\n"
                ttmp = tmp[PluginGlobals.interface_registry[key]]
                ttmp.sort()
                if len(ttmp) == 0:
                    s += "     None\n"
                else:
                    for item in ttmp:
                        s += "     "+item+"\n"
                s += "\n"
            s += "--------------------------------------------------------------\n"
            s += " Registered Plugins by Python Module\n"
            s += "--------------------------------------------------------------\n"
            tmp = {}
            for env in PluginGlobals.env_stack:
                for key in env.plugin_registry:
                    tmp.setdefault(env.plugin_registry[key].__module__,[]).append(key)
            keys = list(tmp.keys())
            keys.sort()
            for key in keys:
                if key == "":                   #pragma:nocover
                    s += " `"+str(key)+"`\n"
                else:
                    s += " "+str(key)+"\n"
                ttmp = tmp[key]
                ttmp.sort()
                for item in ttmp:
                    s += "     "+item+"\n"
                s += "\n"
        s += "--------------------------------------------------------------\n"
        s += " Services for Registered Environments\n"
        s += "--------------------------------------------------------------\n"
        keys = list(PluginGlobals.env_registry.keys())
        keys.sort()
        if 'show_ids' in kwds:
            show_ids = kwds['show_ids']
        else:
            show_ids = True
        for key in keys:
            s += PluginGlobals.env(key).pprint(show_ids=show_ids)
            s += "\n"
        s += "--------------------------------------------------------------\n"
        print(s)


class InterfaceMeta(type):
    """Meta class that registered the declaration of an interface"""

    def __new__(cls, name, bases, d):
        """Register this interface"""
        if name == "Interface":
            d['__interface_namespace__'] = 'pca'
        else:
            d['__interface_namespace__'] = PluginGlobals.env().name
        new_class = type.__new__(cls, name, bases, d)
        if name != "Interface":
            if name in list(PluginGlobals.interface_registry.keys()):
                raise PluginError("Interface %s has already been defined" % name)
            PluginGlobals.interface_registry[name] = new_class
        return new_class


class Interface(with_metaclass(InterfaceMeta,object)):
    """
    Marker base class for extension point interfaces.  This class
    is not intended to be instantiated.  Instead, the declaration
    of subclasses of Interface are recorded, and these
    classes are used to define extension points.
    """
    pass


class ExtensionPoint(object):
    """Marker class for extension points in services."""

    def __init__(self, *args):
        """Create the extension point.

        @param interface: the `Interface` subclass that defines the protocol
            for the extension point
        @param env: the `PluginEnvironment` instance that this extension point
            references
        """
        #
        # Construct the interface, passing in this extension
        #
        nargs=len(args)
        if nargs == 0:
            raise PluginError("Must specify interface class used in the ExtensionPoint")
        self.interface = args[0]
        self.env = [ PluginGlobals.env(self.interface.__interface_namespace__) ]
        if nargs > 1:
            for arg in args[1:]:
                if isinstance(arg,six.string_types):
                    self.env.append( PluginGlobals.env(arg) )
                else:
                    self.env.append(arg)
        self.__doc__ = 'List of services that implement `%s`' % self.interface.__name__

    def __iter__(self):
        """
        Return an iterator to a set of services that match the interface of this
        extension point.
        """
        return self.extensions().__iter__()

    def __call__(self, key=None, all=False):
        """
        Return a set of services that match the interface of this
        extension point.
        """
        if type(key) in six.integer_types:
            #
            # Q: should this be a warning?  A user _might_ be trying
            # to use an integer as a key.  But in practice that's not
            # likely.
            #
            raise PluginError("Access of the n-th extension point is disallowed.  This is not well-defined, since ExtensionPoints are stored as unordered sets.")
        return self.extensions(all=all, key=key)

    def service(self, key=None, all=False):
        """
        Return the unique service that matches the interface of this
        extension point.  An exception occurs if no service matches the
        specified key, or if multiple services match.
        """
        ans = ExtensionPoint.__call__(self, key=key, all=all)
        if len(ans)== 1:
            #
            # There is a single service, so return it.
            #
            return ans.pop()
        elif len(ans) == 0:
            return None
        else:
            raise PluginError("The ExtensionPoint does not have a unique service!  %d services are defined for interface %s.  (key=%s)" % (len(ans), self.interface. __name__, str(key)))

    def __len__(self):
        """
        Return the number of services that match the interface of this
        extension point.
        """
        return len(self.extensions())

    def extensions(self, all=False, key=None):
        """
        Return a set of services that match the interface of this
        extension point.  This tacitly filters out disabled extension points.
        """
        ans = set()
        for env in self.env:
            ans.update(env.active_services(self.interface, all=all, key=key))

        return sorted( ans, key=lambda x:x.id )

    def __repr__(self):
        """Return a textual representation of the extension point."""
        env_str = ""
        for env in self.env:
            env_str += " env=%s" % env.name
        return '<ExtensionPoint %s%s>' % (self.interface.__name__,env_str)


"""
The environment for the components in the PCA.

This class has the following attributes that a user may use:

* name - A string that identifies this environment.  By default a unique integer id is used to define the name "env.<id>"
* namespace - A name the defines the relationship of this environment to other environments
* registry - A map from interfaces to registered services that match each interface
* services - The set of all services (Plugin instances) that have been registered in this environment
* singleton_services - Singleton services, which can only be registered once in each environment
* enabled - A cache that denotes whether a service has been enabled.

The namespace of Environment instances is dynamically generated by extending the namespace of the current environment.  However, the environment namespace can be explicitly declared in the constructor.
"""
class PluginEnvironment(object):

    def __init__(self, name=None, bootstrap=False):
        # The registry of plugins, by name
        self.plugin_registry = {}
        if name is None:
            self.name = "env"+str(PluginGlobals.next_id())
        else:
            self.name = name
        if self.name in PluginGlobals.env_registry:
            raise PluginError("The Environment %r already exists!" % self.name)
        PluginGlobals.env_registry[self.name] = self
        self.singleton_services={}
        self.services=set()
        if not bootstrap:
            self.loaders = ExtensionPoint(IPluginLoader)
            self.loader_paths = ExtensionPoint(IPluginLoadPath)
        self.log = logger_factory(self.name)
        if __debug__:
            self.log.debug("Creating PluginEnvironment %r" % self.name)
        self.level = []
        self.clear_cache()

    def __del__(self):
        #
        # Don't delete the two standard environments.
        #
        if self.name == 'pca' or self.name == '<default>':
            return
        #
        # If the PluginGlobals.clear() method is being called, then
        # don't try to remove data from the environment registry.  It
        # has already been deleted!
        #
        if not PluginGlobals.clearing:
            if self.name in PluginGlobals.env_registry:
                del PluginGlobals.env_registry[self.name]

    def __contains__(self, cls):
        """
        Return whether the given service is in the set of services.
        """
        return cls in self.services

    def active_services(self, cls, all=False, key=None):
        """
        Return the services that have been activated for a specific interface class.
        """
        if isinstance(cls,Plugin):
            id = cls.__class__
        else:
            id = cls
        try:
            return self._cache[id,all,key]
        except KeyError:
            if not issubclass(id,Interface):
                raise PluginError("PluginEnvironment[x] expects "+str(id)+" to be an Interface class")
            strkey = str(key)
            tmp = [x for x in self.services if id in x.__interfaces__ and (all or x.enabled()) and (key is None or x.name == strkey)]
            self._cache[id,all,key]=tmp
            return tmp

    def activate(self, service):
        """
        This adds the service to this environment.
        """
        self.log.info("Adding service %s to environment %s" % (service.name, self.name))
        self.services.add(service)
        self.clear_cache()

    def deactivate(self, service):
        """
        This removes the service from this environment.
        """
        self.log.info("Removing service %s from environment %s" % (service.name, self.name))
        if service in self.services:
            self.services.remove(service)
        self.clear_cache()

    def __repr__(self):
        return self.pprint()

    def pprint(self, show_ids=True):
        """
        Provides a detailed summary of this environment
        """
        s = ""
        s += " Services for Environment %r\n" % self.name
        flag=True
        tmp = {}
        for service in self.services:
            tmp[str(service)] = service
        keys = list(tmp.keys())
        keys.sort()
        for key in keys:
            flag=False
            s += "   "+key
            if show_ids:
                s += "  ("
                if not tmp[key].enabled():
                    s += "-"                    #pragma:nocover
                s += str(tmp[key].id)
                if tmp[key].__class__ in self.singleton_services:
                    s += "*"
                s += ")\n"
            else:
                s += "\n"
        if flag:
            s += "   None\n"
        return s

    def load_services(self, path=None, auto_disable=False, name_re=True):
        """Load services from IPluginLoader extension points"""
        #
        # Construct the search path
        #
        search_path = []
        if not path is None:
            if isinstance(path,six.string_types):
                search_path.append(path)
            elif type(path) is list:
                search_path += path
            else:
                raise PluginError("Unknown type of path argument: "+str(type(path)))
        for item in self.loader_paths:
            search_path += item.get_load_path()
        self.log.info("Loading services to environment %s from search path %s" % (self.name, search_path))
        #
        # Compile the enable expression
        #
        if type(auto_disable) is bool:
            if auto_disable:
                disable_p = re.compile("")
            else:
                disable_p = re.compile("^$")
        else:
            disable_p = re.compile(auto_disable)
        #
        # Compile the name expression
        #
        if type(name_re) is bool:
            if name_re:
                name_p = re.compile("")
            else:                           #pragma:nocover
                raise PluginError("It doesn't make sense to specify name_re=False")
        else:
            name_p = re.compile(name_re)

        for loader in self.loaders:
            loader.load(self, search_path, disable_p, name_p)
        self.clear_cache()

    def clear_cache(self):
        """ Clear the cache of active services """
        self._cache = {}


#
# Reset the plugins environment when this module is first loaded.
#
PluginGlobals.clear(bootstrap=True)
PluginGlobals.push_env("pca")


class IPluginLoader(Interface):
    """An interface for loading plugins."""

    def load(self, env, path, disable_re, name_re):
        """Load plugins found on the specified path.  If disable_re is
        not none, then it is interpreted as a regular expression.  If this
        expression matches the path of a plugin, then that plugin is
        disabled.  Otherwise, the plugin is enabled by default.
        """


class IPluginLoadPath(Interface):

    def get_load_path(self):
        """Returns a list of paths that are searched for plugins"""


class IIgnorePluginWhenLoading(Interface):
    """Interface used by Plugin loaders to identify Plugins that should
    be ignored"""

    def ignore(self, name):
        """Returns true if a loader should ignore a plugin during loading"""


PluginGlobals.env("<default>").loaders = ExtensionPoint(IPluginLoader)
PluginGlobals.env("<default>").loader_paths = ExtensionPoint(IPluginLoadPath)
PluginGlobals.env("pca").loaders = ExtensionPoint(IPluginLoader)
PluginGlobals.env("pca").loader_paths = ExtensionPoint(IPluginLoadPath)


class PluginMeta(type):
    """Meta class for the Plugin class.  This meta class
    takes care of service and extension point registration.  This class
    also instantiates singleton plugins.
    """

    def __new__(cls, name, bases, d):
        """Find all interfaces that need to be registered."""
        #
        # Avoid cycling in the Python logic by hard-coding the behavior
        # for the Plugin and SingletonPlugin classes.
        #
        if name == "Plugin":
            d['__singleton__'] = False
            return type.__new__(cls, name, bases, d)
        if name == "SingletonPlugin":
            d['__singleton__'] = True
            return type.__new__(cls, name, bases, d)
        if name == "ManagedSingletonPlugin":
            #
            # This is a derived class of SingletonPlugin for which
            # we do not need to build an instance
            #
            d['__singleton__'] = True
            return type.__new__(cls, name, bases, d)
        #
        # Check if plugin has already been registered
        #
        if len(d.get('_implements', [])) == 0 and name in PluginGlobals.env().plugin_registry:
            raise PluginError("Plugin class %r does not implement an interface, and it has already been defined in environment '%r'." % (str(name), PluginGlobals.env().name))
        #
        # Capture the environment namespace that this plugin is declared in
        #
        d['__plugin_namespace__'] = PluginGlobals.env().name
        #
        # Find all interfaces that this plugin will support
        #
        __interfaces__ = {}
        for interface in d.get('_implements', {}):
            __interfaces__.setdefault(interface,[]).extend( d['_implements'][interface] )
        for base in [base for base in bases if hasattr(base, '__interfaces__')]:
            for interface in base.__interfaces__:
                __interfaces__.setdefault(interface,[]).extend( base.__interfaces__[interface] )
        d['__interfaces__'] = __interfaces__
        #
        # Create a boolean, which indicates whether this is
        # a singleton class.
        #
        if True in [issubclass(x, SingletonPlugin) for x in bases]:
            d['__singleton__'] = True
        else:
            d['__singleton__'] = False
        #
        # Add interfaces to the list of base classes if they are
        # declared inherited.
        #
        flag=False
        bases = list(bases)
        for interface in d.get('_inherited_interfaces', set()):
            if not interface in bases:
                bases.append(interface)
                flag=True
        if flag:
            cls=MergedPluginMeta
        #
        # Create new class
        #
        new_class = type.__new__(cls, name, tuple(bases), d)
        setattr(new_class,'__name__',name)
        #
        for _interface in __interfaces__:
            if getattr(_interface, '_factory_active', None) is None:
                continue
            for _name,_doc,_subclass in getattr(new_class,"_factory_aliases",[]):
                if _name in _interface._factory_active:
                    if _subclass:
                        continue
                    else:
                        raise PluginError("Alias '%s' has already been defined for interface '%s'" % (_name, str(_interface)))
                _interface._factory_active[_name] = name
                _interface._factory_doc[_name] = _doc
                _interface._factory_cls[_name] = new_class
        #
        if d['__singleton__']:
            #
            # Here, we create an instance of a singleton class, which
            # registers itself in PluginGlobals.singleton_services
            #
            PluginGlobals.singleton_services()[new_class] = True
            __instance__ = new_class()
            PluginGlobals.singleton_services()[new_class] = __instance__
        else:
            __instance__ = None
        setattr(new_class,'__instance__',__instance__)
        setattr(new_class,'__env__',PluginGlobals.env().name)
        #
        # Register this plugin
        #
        PluginGlobals.env().plugin_registry[name] = new_class
        return new_class


class MergedPluginMeta(PluginMeta,InterfaceMeta):

    def __new__(cls, name, bases, d):
        return PluginMeta.__new__(cls, name, bases, d)


class Plugin(with_metaclass(PluginMeta,object)):
    """Base class for plugins.  A 'service' is an instance of a Plugin.

    Every Plugin class can declare what extension points it provides, as
    well as what extension points of other Plugins it extends.
    """

    def __del__(self):
        pass

    def __init__(self, **kwargs):
        if "name" in kwargs:
            self.name=kwargs["name"]

    def __new__(cls, *args, **kwargs):
        """Plugin constructor"""
        #
        # If this service is a singleton, then allocate and configure
        # it differently.
        #
        env = getattr(cls,'__env__',None)
        if cls in PluginGlobals.singleton_services(env):       #pragma:nocover
            self = PluginGlobals.singleton_services(env)[cls]
            if self is True:
                self = super(Plugin, cls).__new__(cls)
                self.id=PluginGlobals.next_id()
                self.name = self.__class__.__name__
                self.activate()
            self._enable = True
            cls.__instance__ = self
            return self
        self = super(Plugin, cls).__new__(cls)
        #
        # Set unique instance id value
        #
        self.id=PluginGlobals.next_id()
        self.name = "Plugin."+str(self.id)
        self._enable = True
        cls.__instance__ = None
        if getattr(cls,'_service',True):
            self.activate()
        return self

    @staticmethod
    def alias(name, doc=None, subclass=False):
        """
        This function is used to declare aliases that can be used by a factory for constructing
        plugin instances.

        When the subclass option is True, then subsequent calls to alias() with this class name
        are ignored, because they are assumed to be due to subclasses of the original class
        declaration.
        """
        frame = sys._getframe(1)
        locals_ = frame.f_locals
        assert locals_ is not frame.f_globals and '__module__' in locals_, \
               'register() can only be used in a class definition'
        locals_.setdefault('_factory_aliases', set()).add((name,doc,subclass))

    @staticmethod
    def implements(interface, namespace=None, inherit=False, service=True):
        """
        Can be used in the class definition of `Plugin` subclasses to
        declare the extension points that are implemented by this
        interface class.

        If the `inherits` option is True, then this `Plugin` class
        inherits from the `interface` class.
        """
        frame = sys._getframe(1)
        locals_ = frame.f_locals
        #
        # Some sanity checks
        #
        assert namespace is None or isinstance(namespace,str), \
               'second implements() argument must be a string'
        assert locals_ is not frame.f_globals and '__module__' in locals_, \
               'implements() can only be used in a class definition'
        #
        if namespace is None:
            namespace = interface.__interface_namespace__
        if inherit:
            locals_.setdefault('_inherited_interfaces', set()).add(interface)
        locals_.setdefault('_implements', {}).setdefault(interface,[]).append(namespace)
        locals_['_service'] = service

    def __repr__(self):
        """Return a textual representation of the plugin."""
        if self.__class__.__name__ == self.name:
            return '<Plugin %s>' % (self.__class__.__name__)
        else:
            return '<Plugin %s %r>' % (self.__class__.__name__, self.name)

    def activate(self):
        """
        Add this service to the global environment, and environments that manage the service's
        interfaces.
        """
        for interface in self.__interfaces__:
            for ns in self.__interfaces__[interface]:
                PluginGlobals.env(ns).activate(self)
        PluginGlobals.env(self.__plugin_namespace__).activate(self)
        return self

    def deactivate(self):
        """
        Remove this service from the global environment, and environments that manage the service's
        interfaces.
        """
        for interface in self.__interfaces__:
            for ns in self.__interfaces__[interface]:
                PluginGlobals.env(ns).deactivate(self)
        PluginGlobals.env(self.__plugin_namespace__).deactivate(self)
        return self

    def disable(self):
        """Disable this plugin."""
        self._enable = False
        #
        # Clear the cache for environments that use this plugin
        #
        for interface in self.__interfaces__:
            for ns in self.__interfaces__[interface]:
                PluginGlobals.env(ns).clear_cache()
        PluginGlobals.env(self.__plugin_namespace__).clear_cache()

    def enable(self):
        """Enable this plugin."""
        self._enable = True
        #
        # Clear the cache for environments that use this plugin
        #
        for interface in self.__interfaces__:
            for ns in self.__interfaces__[interface]:
                PluginGlobals.env(ns).clear_cache()
        PluginGlobals.env(self.__plugin_namespace__).clear_cache()

    def enabled(self):
        """Can be overriden to control whether a plugin is enabled."""
        return self._enable

alias = Plugin.alias
implements = Plugin.implements


class SingletonPlugin(Plugin):
    """The base class for singleton plugins.  The PluginMeta class
    instantiates a SingletonPlugin class when it is declared.  Note that
    only one instance of a SingletonPlugin class is created in
    any environment.
    """
    pass


def CreatePluginFactory(_interface):
    if getattr(_interface, '_factory_active', None) is None:
        setattr(_interface, '_factory_active', {})
        setattr(_interface, '_factory_doc', {})
        setattr(_interface, '_factory_cls', {})
        setattr(_interface, '_factory_deactivated', {})

    class PluginFactoryFunctor(object):
        def __call__(self, _name=None, args=[], **kwds):
            if _name is None:
                return self
            _name=str(_name)
            if not _name in _interface._factory_active:
                return None
            return PluginFactory(_interface._factory_cls[_name], args, **kwds)
        def services(self):
            return list(_interface._factory_active.keys())
        def get_class(self, name):
            return _interface._factory_cls[name]
        def doc(self, name):
            tmp = _interface._factory_doc[name]
            if tmp is None:
                return ""
            return tmp
        def deactivate(self, name):
            if name in _interface._factory_active:
                _interface._factory_deactivated[name] = _interface._factory_active[name]
                del _interface._factory_active[name]
        def activate(self, name):
            if name in _interface._factory_deactivated:
                _interface._factory_active[name] = _interface._factory_deactivated[name]
                del _interface._factory_deactivated[name]
    return PluginFactoryFunctor()


def PluginFactory(classname, args=[], env=None, **kwds):
    """Construct a Plugin instance, and optionally assign it a name"""
    if isinstance(classname, six.string_types):
        try:
            if isinstance(env, six.string_types):
                env = PluginGlobals.env(env)
            elif env is None:
                env = PluginGlobals.env()
            cls = env.plugin_registry[classname]
        except KeyError:
            raise PluginError("Unknown class %r in environment %r" % (str(classname), env.name))
    else:
        cls = classname
    obj = cls(*args, **kwds)
    if 'name' in kwds:
        obj.name = kwds['name']
    if __debug__:
        if obj is None:
            PluginGlobals.env().log.debug("Failed to create plugin %s" % (classname))
        else:
            PluginGlobals.env().log.debug("Creating plugin %s with name %s" % (classname, obj.name))
    return obj


#
# Copyright (C) 2003-2008 Edgewall Software
# Copyright (C) 2003-2004 Jonas Borgstram <jonas@edgewall.com>
# Copyright (C) 2004-2005 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Jonas Borgstram <jonas@edgewall.com>
#         Christopher Lenz <cmlenz@gmx.de>
