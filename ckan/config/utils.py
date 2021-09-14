# -*- coding: utf-8 -*-

import textwrap
import pathlib
import logging

from collections import OrderedDict
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    NewType,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import yaml

T = TypeVar("T")
UnsetType = NewType("UnsetType", dict)
ConverterFrom = Callable[[str], T]
ConverterInto = Callable[[T], str]

UNSET = UnsetType({})
DefaultType = Union[T, UnsetType]


log = logging.getLogger(__name__)


class Key:
    """Generic interface for accessing config options.

    In the simplest case, :py:class:`~ckan.plugins.toolkit.key` objects completely
    interchangeable with the corresponding config option names represented by
    string. Example::

        site_url = toolkit.key().ckan.site_url
        # or
        site_url = toolkit.key(["ckan", "site_url"])
        # or
        site_url = toolkit.key.from_string("ckan.site_url")

        assert site_url == "ckan.site_url"
        assert toolkit.config[site_url] is toolkit.config["ckan.site_url"]

    In addition, :py:class:`~ckan.plugins.toolkit.key` objects are similar to the
    curried functions. Existing :py:class:`~ckan.plugins.toolkit.key` can be extended
    to the sub-key at any moment. Example::

        ckan = toolkit.key().ckan
        assert ckan == "ckan"

        auth = ckan.auth
        assert auth == "ckan.auth"

        unowned = auth.create_unowned_datasets
        assert unowned == "ckan.auth.create_unowned_datasets"
        assert unowned == toolkit.key().ckan.auth.create_unowned_datasets

    """

    __slots__ = "__path"
    __path: Tuple[str, ...]

    def __init__(self, path: Sequence[str] = ()):
        self.__path = tuple(path)

    def __str__(self):
        return ".".join(self.__path)

    def __repr__(self):
        return f"<Key {self}>"

    def __len__(self):
        return len(self.__path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: Any):
        if isinstance(other, str):
            return str(self) == other

        elif isinstance(other, Key):
            return self.__path == other.__path

        return super().__eq__(other)

    def __add__(self, other: Any):
        return self._combine(self, other)

    def __radd__(self, other: Any):
        return self._combine(other, self)

    def __getitem__(self, idx):
        fragment = self.__path[idx]
        if isinstance(fragment, tuple):
            return Key(fragment)
        return fragment

    def __getattr__(self, fragment: str):
        return self._descend(fragment)

    def _descend(self, fragment: str) -> "Key":
        """Create sub-key."""
        return Key(self.__path + (fragment,))

    def _ascend(self) -> "Key":
        """Get parent key for the current one.

        Explicit version of `key[:-1]`.
        """
        return Key(self.__path[:-1])

    @classmethod
    def _as_key(cls, value: Any):
        if isinstance(value, Key):
            return value

        if isinstance(value, str):
            return cls.from_string(value)

        type_ = type(value).__name__
        raise TypeError(f"{type_} cannot be converted into Key")

    @staticmethod
    def from_string(path: str):
        return Key([fragment for fragment in path.split(".") if fragment])

    @staticmethod
    def _combine(left: Any, right: Any):
        head = Key._as_key(left)
        tail = Key._as_key(right)

        return Key(head.__path + tail.__path)


class Details(Generic[T]):
    default: DefaultType[T]
    commented: bool = False
    description: Optional[str] = None

    def __init__(self, default: DefaultType[T] = UNSET):
        self.default = default

    def __str__(self):
        if self.has_default():
            return str(self.default)
        return ""

    def has_default(self):
        return self.default is not UNSET

    def set_description(self, description: str):
        self.description = description
        return self

    def set_default(self, default: T):
        self.default = default
        return self

    def comment(self):
        self.commented = True
        return self


class Annotation(str):
    pass


class Declaration:
    _mapping: Dict[Key, Details[Any]]
    _order: List[Union[Key, Annotation, Any]]

    def reset(self):
        self._mapping = OrderedDict()
        self._order = []

    def load_core_declaration(self):
        source = pathlib.Path(__file__).parent / "config_declaration.yaml"
        with source.open("r") as stream:
            data = yaml.safe_load(stream)
            self.load_dict(data)

    def load_plugin(self, name: str):
        from ckan.plugins.core import _get_service

        plugin: Any = _get_service(name)
        if not plugin:
            log.error("Plugin %s does not exists", name)
            return
        plugin.declare_config_options(self, Key())

    def load_dict(self, data: Dict[str, Any]):
        import ckan.logic.schema as schema
        from ckan.logic import ValidationError
        from ckan.lib.navl.dictization_functions import validate

        version = data["version"]
        if version == 1:
            data, errors = validate(data, schema.config_declaration_v1())
            if any(
                details
                for item in errors["items"]
                for details in item["details"]
            ):
                raise ValidationError(errors)
            for group in data["items"]:
                if "annotation" in group:
                    self.annotate(group["annotation"])
                for details in group["details"]:
                    option = self.declare(details["key"], details["default"])
                    if details["commented"]:
                        option.comment()
                    if details["description"]:
                        option.set_description(details["description"])

    def __init__(self):
        self.reset()

    def __getitem__(self, key: Key) -> Details[Any]:
        return self._mapping[key]

    def __str__(self):
        result = ""
        for item in self._order:
            if isinstance(item, Key):
                value = self._mapping[item]
                if value.description:
                    result += (
                        textwrap.fill(
                            value.description,
                            initial_indent="# ",
                            subsequent_indent="# ",
                        )
                        + "\n"
                    )

                result += "{comment}{key} = {value}\n".format(
                    comment="# " if value.commented else "",
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

    def declare(self, key: Key, default: DefaultType[T] = UNSET) -> Details[T]:
        value = Details(default)
        if key not in self._mapping:
            self._order.append(key)

        self._mapping[key] = value
        return value

    def annotate(self, annotation: str):
        self._order.append(Annotation(annotation))
