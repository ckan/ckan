"""Base code units used by plugin system.

This module contains adapted and simplified version of pyutilib plugin system
that was used historically by CKAN.

"""

from __future__ import annotations

import sys

from typing import Any
from typing_extensions import ClassVar, TypeVar

TSingleton = TypeVar("TSingleton", bound="SingletonPlugin")


class PluginException(Exception):
    """Exception base class for plugin errors."""


class ExistingInterfaceException(PluginException):
    """Interface with the same name already exists."""

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"Interface {self.name} has already been defined"


class PluginNotFoundException(PluginException):
    """Requested plugin cannot be found."""

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"Plugin {self.name} does not exist"


class Interface:
    """Base class for custom interfaces.

    Marker base class for extension point interfaces.  This class is not
    intended to be instantiated.  Instead, the declaration of subclasses of
    Interface are recorded, and these classes are used to define extension
    points.

    Example:
    >>> class IExample(Interface):
    >>>     def example_method(self):
    >>>         pass
    """

    # force PluginImplementations to iterate over interface in reverse order
    _reverse_iteration_order: ClassVar[bool] = False

    # collection of interface-classes extending base Interface. This is used to
    # guarantee unique names of interfaces.
    _interfaces: ClassVar[set[type[Interface]]] = set()

    # there is no practical use of `name` attribute in interface, because
    # interfaces are never instantiated. But declaring this attribute
    # simplifies typing when iterating over interface implementations.
    name: str

    def __init_subclass__(cls, **kwargs: Any):
        """Prevent interface name duplication when interfaces are created."""

        # `implements(..., inherit=True)` adds interface to the list of
        # plugin's bases. There is no reason to disallow identical plugin-class
        # names, so this scenario stops execution early.
        if isinstance(cls, Plugin):
            return

        if cls in Interface._interfaces:
            raise ExistingInterfaceException(cls.__name__)

        Interface._interfaces.add(cls)

    @classmethod
    def provided_by(cls, instance: Plugin) -> bool:
        """Check that the object is an instance of the class that implements
        the interface.

        Example:
        >>> activity = get_plugin("activity")
        >>> assert IConfigurer.provided_by(activity)
        """
        return cls.implemented_by(type(instance))

    @classmethod
    def implemented_by(cls, other: type[Plugin]) -> bool:
        """Check whether the class implements the current interface.

        Example:
        >>> assert IConfigurer.implemented_by(ActivityPlugin)

        """
        try:
            return issubclass(other, cls) or cls in other._implements
        except AttributeError:
            return False


class PluginMeta(type):
    """Metaclass for plugins that initializes supplementary attributes required
    by interface implementations.

    """

    def __new__(cls, name: str, bases: tuple[type, ...], data: dict[str, Any]):
        data.setdefault("_implements", set())
        data.setdefault("_inherited_interfaces", set())

        # add all interfaces with `inherit=True` to the bases of plugin
        # class. It adds default implementation of methods from interface to
        # the plugin's class
        bases += tuple(data["_inherited_interfaces"] - set(bases))

        # copy interfaces implemented by the parent classes into a new one to
        # correctly identify if interface is provided_by/implemented_by the new
        # class.
        for base in bases:
            data["_implements"].update(getattr(base, "_implements", set()))

        return super().__new__(cls, name, tuple(bases), data)


class Plugin(metaclass=PluginMeta):
    """Base class for plugins which require multiple instances.

    Unless you need multiple instances of your plugin object you should
    probably use SingletonPlugin.

    """

    # collection of all interfaces implemented by the plugin. Used by
    # `Interface.implemented_by` check
    _implements: ClassVar[set[type[Interface]]]

    # collection of interfaces implemented with `inherit=True`. These
    # interfaces are added as parent classes to the plugin
    _inherited_interfaces: ClassVar[set[type[Interface]]]

    # name of the plugin instance. All known plugins are instances of
    # `SingletonPlugin`, so it may be converted to ClassVar in future. Right
    # now it's kept as instance variable for compatibility with original
    # implementation from pyutilib
    name: str

    def __init__(self, *args: Any, **kwargs: Any):
        name = kwargs.pop("name", None)
        if not name:
            name = self.__class__.__name__
        self.name = name

    def __str__(self):
        return f"<Plugin {self.name}>"


class SingletonPlugin(Plugin):
    """Base class for plugins which are singletons (ie most of them)

    One singleton instance of this class will be created when the plugin is
    loaded. Subsequent calls to the class constructor will always return the
    same singleton instance.
    """

    def __new__(cls, *args: Any, **kwargs: Any):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)

        return cls._instance


def implements(interface: type[Interface], inherit: bool = False):
    """Can be used in the class definition of `Plugin` subclasses to
    declare the extension points that are implemented by this
    interface class.

    Example:
    >>> class MyPlugin(Plugin):
    >>>     implements(IConfigurer, inherit=True)

    If compatibility with CKAN pre-v2.11 is not required, plugin class should
    extend interface class.

    Example:
    >>> class MyPlugin(Plugin, IConfigurer):
    >>>     pass
    """
    frame = sys._getframe(1)
    locals_ = frame.f_locals
    locals_.setdefault("_implements", set()).add(interface)
    if inherit:
        locals_.setdefault("_inherited_interfaces", set()).add(interface)
