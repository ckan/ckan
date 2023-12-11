from __future__ import annotations
from typing import Any
from typing_extensions import ClassVar, TypeVar

TSingleton = TypeVar("TSingleton", bound="SingletonPlugin")


class PluginException(Exception):
    """Exception base class for plugin errors."""


class ExistingInterfaceException(PluginException):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"Interface {self.name} has already been defined"


class PluginNotFoundException(PluginException):
    """Raised when a requested plugin cannot be found."""

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"Interface {self.name} does not exist"


class Interface:
    """Base class for custom interfaces.

    Marker base class for extension point interfaces.  This class is not
    intended to be instantiated.  Instead, the declaration of subclasses of
    Interface are recorded, and these classes are used to define extension
    points.

    """
    # force PluginImplementations to iterate over interface in reverse order
    _reverse_iteration_order: ClassVar[bool] = False

    _interfaces: set[type[Interface]] = set()

    name: str

    def __init_subclass__(cls, **kwargs: Any):
        if isinstance(cls, Plugin):
            return

        if cls in Interface._interfaces:
            raise ExistingInterfaceException(cls.__name__)

        Interface._interfaces.add(cls)

    @classmethod
    def provided_by(cls, instance: Plugin) -> bool:
        """Check that the object is an instance of the class that implements
        the interface.
        """
        return cls.implemented_by(type(instance))

    @classmethod
    def implemented_by(cls, other: type[Plugin]) -> bool:
        """Check whether the class implements the current interface."""
        try:
            return bool(cls in other._implements)
        except AttributeError:
            return False


class PluginMeta(type):
    def __new__(cls, name: str, bases: tuple[type, ...], data: dict[str, Any]):
        data.setdefault("_implements", set())
        data.setdefault("_inherited_interfaces", set())

        bases += tuple(data["_inherited_interfaces"] - set(bases))
        return super().__new__(cls, name, tuple(bases), data)

class Plugin(metaclass=PluginMeta):
    """Base class for plugins which require multiple instances.

    Unless you need multiple instances of your plugin object you should
    probably use SingletonPlugin.

    """

    _implements: ClassVar[set[type[Interface]]]
    _inherited_interfaces: ClassVar[set[type[Interface]]]
    name: str

    def __init__(self, *args: Any, **kwargs: Any):
        name = kwargs.pop("name", None)
        if not name:
            name = self.__class__.__name__
        self.name = name


class SingletonPlugin(Plugin):
    """Base class for plugins which are singletons (ie most of them)

    One singleton instance of this class will be created when the plugin is
    loaded. Subsequent calls to the class constructor will always return the
    same singleton instance.
    """
    _instance: SingletonPlugin

    def __new__(cls, *args: Any, **kwargs: Any):

        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)

        return cls._instance
