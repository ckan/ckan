# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from collections import OrderedDict
from typing import (
    Any,
    Container,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Union,
    TYPE_CHECKING,
    cast,
)

from .key import Key, Pattern, Wildcard
from .option import Option, Annotation, Flag, T

from .load import loader, DeclarationDict
from .describe import describer
from .serialize import serializer

if TYPE_CHECKING:
    from ckan.common import CKANConfig

log = logging.getLogger(__name__)

__all__ = ["Declaration", "Key"]

_non_iterable = Flag.non_iterable()


class Declaration:
    __slots__ = (
        "_mapping",
        "_order",
        "_plugins",
        "_core_loaded",
        "_sealed",
    )
    _mapping: Dict[Key, Option[Any]]
    _order: List[Union[Key, Annotation, Any]]
    _plugins: Set[str]
    _sealed: bool
    _core_loaded: bool

    def __init__(self):
        self._reset()

    def __bool__(self):
        return bool(self._order)

    def __contains__(self, key: Key):
        return key in self._mapping

    def __getitem__(self, key: Key) -> Option[Any]:
        return self._mapping[key]

    def get(self, key: Union[str, Key]) -> Optional[Option[Any]]:
        k = Key._as_key(key)
        if k in self:
            return self[k]

    def iter_options(
        self,
        *,
        pattern: Union[str, Pattern] = "*",
        exclude: Flag = _non_iterable,
    ) -> Iterator[Key]:
        if isinstance(pattern, str):
            pattern = Pattern.from_string(pattern)
        for k, v in self._mapping.items():
            if v._has_flag(exclude):
                continue
            if pattern != k:
                continue
            yield k

    def setup(self):
        import ckan.plugins as p

        self._reset()
        self.load_core_declaration()
        for plugin in reversed(
            list(p.PluginImplementations(p.IConfigDeclaration))
        ):
            plugin.declare_config_options(self, Key())
        self._seal()

    def make_safe(self, config: "CKANConfig") -> bool:
        if config.get_value("config.mode") != "strict":
            return False

        for key in self.iter_options(exclude=Flag.not_safe()):
            if key not in config and not isinstance(key, Pattern):
                config[str(key)] = self[key].default
        return True

    def normalize(self, config: "CKANConfig") -> bool:
        import ckan.lib.navl.dictization_functions as df

        if config.get_value("config.mode") != "strict":
            return False

        data, errors = self.validate(config)

        for k, v in data.items():
            if v is df.missing:
                continue

            assert k not in errors, f"Invalid value for {k}: {v}"

            if k not in cast(Container[str], self):
                # it either __extra or __junk
                continue

            if config.get(k) == v:
                continue

            log.debug(f"Normalized {k} config option: {v}")
            config[k] = v

        return True

    def validate(self, config: "CKANConfig"):
        import ckan.lib.navl.dictization_functions as df

        schema = self.into_schema()
        data, errors = df.validate(dict(config), schema)
        return data, errors

    def _reset(self):
        self._mapping = OrderedDict()
        self._order = []
        self._plugins = set()
        self._core_loaded = False
        self._sealed = False

    def _seal(self):
        self._sealed = True

    def load_core_declaration(self):
        if self._core_loaded:
            log.debug("Declaration for core is already loaded")
            return

        loader(self, "core")
        self._core_loaded = True

    def load_plugin(self, name: str):
        if name in self._plugins:
            log.debug("Declaration for plugin %s is already loaded", name)
            return
        loader(self, "plugin", name)

    def load_dict(self, data: DeclarationDict):
        loader(self, "dict", data)

    def into_ini(self, minimal: bool, verbose: bool = False) -> str:
        return serializer(self, "ini", minimal, verbose)

    def into_schema(self) -> Dict[str, Any]:
        return serializer(self, "validation_schema")

    def into_docs(self) -> str:
        return serializer(self, "rst")

    def describe(self, fmt: str) -> str:
        return describer(self, fmt)

    def declare(
        self, key: Union[Key, str], default: Optional[T] = None
    ) -> Option[T]:
        if self._sealed:
            raise TypeError("Sealed declaration cannot be updated")

        if isinstance(key, str):
            key = Key.from_string(key)

        value = Option(default)
        if key in self._mapping:
            raise ValueError(f"{key} already declared")
        self._order.append(key)

        self._mapping[key] = value
        return value

    def declare_bool(
            self, key: Key, default: Optional[bool] = False) -> Option[bool]:
        option = self.declare(key, bool(default))
        option.set_validators("boolean_validator")
        return option

    def declare_int(self, key: Key, default: Optional[int]) -> Option[int]:
        option = self.declare(key, default)
        option.set_validators("convert_int")
        return option

    def declare_list(
            self, key: Key, default: Optional[list[Any]]) -> Option[list[Any]]:
        option = self.declare(key, default)
        option.set_validators("as_list")
        return option

    def declare_dynamic(self, key: Key, default: Any = None) -> Option[Any]:
        key = Pattern(
            [
                Wildcard(fragment[1:-1])
                if (fragment[0], fragment[-1]) == ("<", ">")
                else fragment
                for fragment in key
            ]
        )
        option: Option[Any] = self.declare(key, default)
        return option

    def annotate(self, annotation: str):
        if self._sealed:
            raise TypeError("Sealed declaration cannot be updated")

        self._order.append(Annotation(annotation))
