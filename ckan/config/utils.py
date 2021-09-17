# -*- coding: utf-8 -*-

import fnmatch
import enum
from io import StringIO
import textwrap
import pathlib
import logging

from collections import OrderedDict
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    NewType,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import yaml
from werkzeug.utils import import_string

T = TypeVar("T")
UnsetType = NewType("UnsetType", dict)
ConverterFrom = Callable[[str], T]
ConverterInto = Callable[[T], str]

UNSET = UnsetType({})
DefaultType = Union[T, UnsetType]

log = logging.getLogger(__name__)


class Flag(enum.Flag):
    disabled = enum.auto()
    ignored = enum.auto()
    experimental = enum.auto()
    internal = enum.auto()


class Key:
    """Generic interface for accessing config options.

    In the simplest case, :py:class:`~ckan.plugins.toolkit.key` objects completely
    interchangeable with the corresponding config option names represented by
    string. Example::

        site_url = toolkit.key.ckan.site_url
        # or
        site_url = toolkit.key.from_iterable(["ckan", "site_url"])
        # or
        site_url = toolkit.key.from_string("ckan.site_url")

        assert site_url == "ckan.site_url"
        assert toolkit.config[site_url] is toolkit.config["ckan.site_url"]

    In addition, :py:class:`~ckan.plugins.toolkit.key` objects are similar to the
    curried functions. Existing :py:class:`~ckan.plugins.toolkit.key` can be extended
    to the sub-key at any moment. Example::

        ckan = toolkit.key.ckan
        assert ckan == "ckan"

        auth = ckan.auth
        assert auth == "ckan.auth"

        unowned = auth.create_unowned_datasets
        assert unowned == "ckan.auth.create_unowned_datasets"
        assert unowned == toolkit.key.ckan.auth.create_unowned_datasets

    """

    __slots__ = ("_path",)
    _path: Tuple[str, ...]

    def __init__(self, path: Iterable[str] = ()):
        self._path = tuple(path)

    def __str__(self):
        return ".".join(self._path)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self}>"

    def __len__(self):
        return len(self._path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: Any):
        if isinstance(other, str):
            return str(self) == other

        elif isinstance(other, Key):
            return self._path == other._path

        return super().__eq__(other)

    def __add__(self, other: Any):
        return self._combine(self, other)

    def __radd__(self, other: Any):
        return self._combine(other, self)

    def __getitem__(self, idx):
        fragment = self._path[idx]
        if isinstance(fragment, tuple):
            return self.__class__(fragment)
        return fragment

    def __getattr__(self, fragment: str):
        return self._descend(fragment)

    def __iter__(self):
        return iter(self._path)

    def _descend(self, fragment: str):
        """Create sub-key."""
        return self.__class__(self._path + (fragment,))

    def _ascend(self):
        """Get parent key for the current one.

        Explicit version of `key[:-1]`.
        """
        return self.__class__(self._path[:-1])

    @classmethod
    def _as_key(cls, value: Any):
        if isinstance(value, Key):
            return value

        if isinstance(value, str):
            return cls.from_string(value)

        try:
            return cls(value)
        except TypeError:
            type_ = type(value).__name__
            raise TypeError(f"{type_} cannot be converted into Key")

    @classmethod
    def _combine(cls, left: Any, right: Any):
        head = cls._as_key(left)
        tail = cls._as_key(right)

        return cls(head._path + tail._path)

    @classmethod
    def from_string(cls, path: str):
        return cls([fragment for fragment in path.split(".") if fragment])

    @classmethod
    def from_iterable(cls, path: Iterable[str]):
        return cls(path)


class Pattern(Key):
    __slots__ = ()

    def __eq__(self, other: Any):
        if isinstance(other, str):
            other = Pattern.from_string(other)

        if isinstance(other, Key):
            return fnmatch.fnmatch(str(other), str(self))

        return super().__eq__(other)


class Option(Generic[T]):
    __slots__ = ("flags", "default", "description", "_validators")

    flags: Flag
    default: DefaultType[T]
    description: Optional[str]
    _validators: List[Any]

    def __init__(self, default: DefaultType[T] = UNSET):
        self.default = default
        self.description = None
        self._validators = []
        self.flags = Flag(0)

    def __str__(self):
        if self.has_default():
            return str(self.default)
        return ""

    def _unset_flag(self, flag: Flag):
        self.flags &= ~flag

    def _set_flag(self, flag: Flag):
        self.flags |= flag

    def _has_flag(self, flag: Flag) -> bool:
        return bool(self.flags & flag)

    def has_default(self):
        return self.default is not UNSET

    def set_default(self, default: T):
        self.default = default
        return self

    def set_description(self, description: str):
        self.description = description
        return self

    def set_validators(self, validators: List[Any]):
        from ckan.logic import get_validator

        if self.has_default():
            default_validator = get_validator("default")(self.default)
            validators = [default_validator] + validators
        self._validators = validators

    def get_validators(self):
        return self._validators

    def disable(self):
        self._set_flag(Flag.disabled)

    def ignore(self):
        self._set_flag(Flag.ignored)

    def experimental(self):
        self._set_flag(Flag.experimental)

    def internal(self):
        self._set_flag(Flag.internal)


class Annotation(str):
    pass


class Declaration:
    __slots__ = (
        "_mapping",
        "_order",
        "_loader",
        "_serializer",
        "_plugins",
        "_core_loaded",
        "_sealed",
    )
    _mapping: Dict[Key, Option[Any]]
    _order: List[Union[Key, Annotation, Any]]
    _plugins: Set[str]
    _loader: "Loader"
    _serializer: "Serializer"
    _sealed: bool
    _core_loaded: bool

    def __init__(self):
        self.reset()
        self._loader = Loader(self)
        self._serializer = Serializer(self)

    def __bool__(self):
        return bool(self._order)

    def __getitem__(self, key: Key) -> Option[Any]:
        return self._mapping[key]

    def iter_options(
        self,
        *,
        pattern: str = "*",
        exclude: Flag = Flag.ignored | Flag.experimental,
    ) -> Iterator[Key]:
        pat = Pattern.from_string(pattern)
        for k, v in self._mapping.items():
            if not isinstance(v, Option):
                continue
            if v._has_flag(exclude):
                continue
            if k != pat:
                continue
            yield k

    def reset(self):
        self._mapping = OrderedDict()
        self._order = []
        self._plugins = set()
        self._core_loaded = False
        self._sealed = False

    def seal(self):
        self._sealed = True

    def load_core_declaration(self):
        if self._core_loaded:
            log.debug("Declaration for core is already loaded")
            return
        self._core_loaded = True
        self._loader.from_core_declaration()

    def load_plugin(self, name: str):
        if name in self._plugins:
            log.debug("Declaration for plugin %s is already loaded", name)
            return
        self._loader.from_plugin(name)

    def load_dict(self, data: Dict[str, Any]):
        self._loader.from_dict(data)

    def into_ini(self):
        return self._serializer.into_ini()

    def into_schema(self):
        return self._serializer.into_schema()

    def into_declaration(self, fmt: str):
        return self._serializer.into_declaration(fmt)

    def declare(self, key: Key, default: DefaultType[T] = UNSET) -> Option[T]:
        if self._sealed:
            raise TypeError("Sealed declaration cannot be updated")

        value = Option(default)
        if key in self._mapping:
            raise ValueError(f"{key} already declared")
        self._order.append(key)

        self._mapping[key] = value
        return value

    def declare_bool(self, key: Key, default: Any) -> Option[bool]:
        from ckan.logic import get_validator

        option = self.declare(key, bool(default))
        option.set_validators([get_validator("boolean_validator")])
        return option

    def declare_int(self, key: Key, default: int) -> Option[int]:
        from ckan.logic import get_validator

        option = self.declare(key, default)
        option.set_validators([get_validator("convert_int")])
        return option

    def annotate(self, annotation: str):
        if self._sealed:
            raise TypeError("Sealed declaration cannot be updated")

        self._order.append(Annotation(annotation))


option_types = {
    "base": "declare",
    "bool": "declare_bool",
    "int": "declare_int",
}


class Loader:
    __slots__ = ("declaration",)
    declaration: Declaration

    def __init__(self, declaration: Declaration):
        self.declaration = declaration

    def from_core_declaration(self):
        source = pathlib.Path(__file__).parent / "config_declaration.yaml"
        with source.open("r") as stream:
            data = yaml.safe_load(stream)
            self.from_dict(data)

    def from_plugin(self, name: str):
        from ckan.plugins import IConfigDeclaration, PluginNotFoundException
        from ckan.plugins.core import _get_service

        try:
            plugin: Any = _get_service(name)
        except PluginNotFoundException:
            log.error("Plugin %s does not exists", name)
            return

        if not IConfigDeclaration.implemented_by(type(plugin)):
            log.error("Plugin %s does not declare config options", name)
            return

        plugin.declare_config_options(self.declaration, Key())

    def from_dict(self, data: Dict[str, Any]):
        import ckan.logic.schema as schema
        from ckan.logic import ValidationError
        from ckan.lib.navl.dictization_functions import validate

        version = data["version"]
        if version == 1:

            data, errors = validate(data, schema.config_declaration_v1())
            if any(
                options
                for item in errors["groups"]
                for options in item["options"]
            ):
                raise ValidationError(errors)
            for group in data["groups"]:
                if "annotation" in group:
                    self.declaration.annotate(group["annotation"])
                for details in group["options"]:
                    factory = option_types[details["type"]]
                    option: Option = getattr(self.declaration, factory)(
                        details["key"], details["default"]
                    )

                    validators = _validators_from_string(details["validators"])
                    if validators:
                        option.set_validators(validators)

                    for flag in Flag:
                        if details[flag.name]:
                            option._set_flag(flag)

                    if details["description"]:
                        option.set_description(details["description"])

                    if details["default_callable"]:
                        args = details.get("default_args", {})
                        default = import_string(details["default_callable"])(
                            **args
                        )
                        option.set_default(default)


class Serializer:
    __slots__ = ("declaration",)
    declaration: Declaration

    def __init__(self, declaration: Declaration):
        self.declaration = declaration

    def into_ini(self):
        result = ""
        for item in self.declaration._order:
            if isinstance(item, Key):
                option = self.declaration._mapping[item]
                if option._has_flag(
                    Flag.ignored | Flag.experimental | Flag.internal
                ):
                    continue

                if option.description:
                    result += (
                        textwrap.fill(
                            option.description,
                            initial_indent="# ",
                            subsequent_indent="# ",
                        )
                        + "\n"
                    )

                if isinstance(option.default, bool):
                    value = str(option).lower()
                else:
                    value = str(option)

                result += "{comment}{key} = {value}\n".format(
                    comment="# " if option._has_flag(Flag.disabled) else "",
                    key=item,
                    value=value,
                )

            elif isinstance(item, Annotation):
                result += (
                    "\n"
                    + textwrap.fill(
                        item, initial_indent="## ", subsequent_indent="## "
                    )
                    + "\n"
                )

        return result

    def into_schema(self) -> Dict[str, Any]:
        schema = {}
        for key, option in self.declaration._mapping.items():
            schema[str(key)] = option.get_validators()

        return schema

    def into_declaration(self, fmt: str, exclude = Flag.internal | Flag.ignored | Flag.experimental) -> str:

        if fmt == "python":
            describer = PythonDescriber()
        elif fmt == "json":
            describer = JsonDescriber()
        elif fmt == "yaml":
            describer = YamlDescriber()
        elif fmt == "toml":
            describer = TomlDescriber()
        elif fmt == "dict":
            describer = DictDescriber()
        else:
            raise TypeError(f"Cannot generate {fmt} annotation")

        for item in self.declaration._order:
            if isinstance(item, Annotation):
                describer.annotate(item)
            elif isinstance(item, Key):
                option = self.declaration._mapping[item]
                if option._has_flag(exclude):
                    continue
                describer.add_option(item, option)
        return describer.finalize()


class DictDescriber():
    def __init__(self):
        self.data = {"version": 1, "groups": []}
        self.current_listing = None

    def _add_group(self, annotation: Optional[str] = None):
        listing = []
        self.data["groups"].append({
            "annotation": annotation,
            "options": listing
        })
        self.current_listing = listing

    def finalize(self):
        import pprint
        return pprint.pformat(self.data)

    def annotate(self, annotation: str):
        self._add_group(str(annotation))

    def add_option(self, key: Key, option: Option):
        if self.current_listing is None:
            self._add_group()
        data: Dict[str, Any] = {
            "key": str(key),
        }
        if option.has_default():
            data["default"] = option.default

        validators = option.get_validators()
        if validators:
            data["validators"] = " ".join(v.__name__ for v in validators)

        if option._has_flag(Flag.disabled):
            data["disabled"] = True
        if option._has_flag(Flag.ignored):
            data["ignored"] = True
        if option._has_flag(Flag.internal):
            data["internal"] = True
        if option._has_flag(Flag.experimental):
            data["experimental"] = True
        if option.description:
            data["description"] = option.description

        self.current_listing.append(data)


class TomlDescriber(DictDescriber):
    def finalize(self):
        import toml
        return toml.dumps(self.data)


class JsonDescriber(DictDescriber):
    def finalize(self):
        import json
        return json.dumps(self.data)

class YamlDescriber(DictDescriber):
    def finalize(self):
        import yaml
        return yaml.safe_dump(self.data)

class PythonDescriber():
    def __init__(self):
        self.output = StringIO()

    def finalize(self):
        return self.output.getvalue()

    def annotate(self, annotation: str):
        self.output.write(f"\ndeclaration.annotate({repr(annotation)})\n")

    def add_option(self, key: Key, option: Option):
        default = option.default if option.has_default() else str(option)
        self.output.write(f"declaration.declare(key.{key}, {repr(default)})")
        if option._has_flag(Flag.disabled):
            self.output.write(".disable()")
        if option._has_flag(Flag.ignored):
            self.output.write(".ignore()")
        if option._has_flag(Flag.internal):
            self.output.write(".internal()")
        if option._has_flag(Flag.experimental):
            self.output.write(".experimental()")
        if option.description:
            self.output.write(f".set_description({repr(option.description)})")

        validators = option.get_validators()
        if validators:
            validators_str = " ".join(v.__name__ for v in validators)
            self.output.write(f".set_validators([{validators_str})]")

        self.output.write("\n")



# taken from ckanext-scheming
# (https://github.com/ckan/ckanext-scheming/blob/release-2.1.0/ckanext/scheming/validation.py#L407-L426).
# This syntax is familiar for everyone and it we can switch to the original
# when scheming become a part of core.
def _validators_from_string(s: str):
    """
    convert a schema validators string to a list of validators
    e.g. "if_empty_same_as(name) unicode" becomes:
    [if_empty_same_as("name"), unicode]
    """
    from ckan.logic import get_validator

    out = []
    parts = s.split()
    for p in parts:
        if "(" in p and p[-1] == ")":
            name, args = p.split("(", 1)
            args = args[:-1].split(",")  # trim trailing ')', break up
            v = get_validator(name)(*args)
        else:
            v = get_validator(p)
        out.append(v)
    return out
