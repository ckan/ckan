# -*- coding: utf-8 -*-
"""This module contains definition of the config Declaration class.

"""
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


__all__ = ["Declaration", "Key"]

_non_iterable = Flag.non_iterable()

log = logging.getLogger(__name__)


class Declaration:
    """Container for the config declarations.

    This class provides methods for all the common interactions with the config
    declarations. So in most cases, you won't use any other member defined
    under this module directly.

    """
    __slots__ = (
        "_options",
        "_members",
        "_plugins",
        "_core_loaded",
        "_sealed",
    )
    _options: Dict[Key, Option[Any]]
    _members: List[Union[Key, Annotation, Any]]
    _plugins: Set[str]
    _sealed: bool
    _core_loaded: bool

    def __init__(self):
        self._reset()

    def __bool__(self):
        return bool(self._members)

    def __contains__(self, key: Union[Key, str]):
        return key in self._options

    def __getitem__(self, key: Key) -> Option[Any]:
        return self._options[key]

    def get(self, key: Union[str, Key]) -> Optional[Option[Any]]:
        """Return the declaration of config option or `None`.
        """
        k = Key._as_key(key)
        if k in self:
            return self[k]

    def iter_options(
        self,
        *,
        pattern: Union[str, Pattern] = "*",
        exclude: Flag = _non_iterable,
    ) -> Iterator[Key]:
        """Iterate over declared config options.

        Args:
            pattern: only iterate over options that matches the pattern
            exclude: skip options that have given flag.
        """
        if isinstance(pattern, str):
            pattern = Pattern.from_string(pattern)

        for k, v in self._options.items():
            if v.has_flag(exclude):
                continue

            if pattern != k:
                continue

            yield k

    def setup(self):
        """Load all the config declarations from core and enabled plugins.

        This method seals the declaration object, preventing further
        modifications.

        """
        import ckan.plugins as p

        self._reset()
        self.load_core_declaration()
        for plugin in reversed(
            list(p.PluginImplementations(p.IConfigDeclaration))
        ):
            plugin.declare_config_options(self, Key())
        self._seal()

    def make_safe(self, config: "CKANConfig"):
        """Load defaul values for missing options.
        """

        for key in self.iter_options(exclude=Flag.not_safe()):
            if key in config or isinstance(key, Pattern):
                continue

            info = self[key]

            if info.legacy_key and info.legacy_key in config:
                log.warning(
                    "Config option '%s' is deprecated. Use '%s' instead",
                    info.legacy_key,
                    key
                )
                config[str(key)] = config[info.legacy_key]

            else:
                config[str(key)] = info.default

    def normalize(self, config: "CKANConfig"):
        """Validate and normalize all the values in the config object.

        This method ensures that all the config values are in-place and
        converts them to the expected type. If config option doesn't pass
        validation value is left unprocessed, as a string.

        """
        import ckan.lib.navl.dictization_functions as df

        data, errors = self.validate(config)

        for k, v in data.items():
            if v is df.missing:
                continue

            if k not in cast(Container[str], self):
                # it either __extra or __junk
                continue

            if k in errors:
                continue

            if config.get(k) == v:
                continue

            log.debug(f"Normalized {k} config option: {v}")
            config[k] = v

    def validate(
            self, config: "CKANConfig"
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return validated config dict and dictionary with validation errors.
        """
        import ckan.lib.navl.dictization_functions as df

        schema = self.into_schema()
        data, errors = df.validate(dict(config), schema)
        return data, errors

    def _reset(self):
        """Unseal declaration and remove all the options, making it ready for
        the new definitions.

        """
        self._options = OrderedDict()
        self._members = []
        self._plugins = set()
        self._core_loaded = False
        self._sealed = False

    def _seal(self):
        """Prevent further modifications of the declaration object.
        """
        self._sealed = True

    def load_core_declaration(self):
        """Load CKAN core declarations(no plugins are loaded).
        """
        if self._core_loaded:
            log.debug("Declaration for core is already loaded")
            return

        loader(self, "core")
        self._core_loaded = True

    def load_plugin(self, name: str):
        """Load declarations from the enabled plugin.
        """
        if name in self._plugins:
            log.debug("Declaration for plugin %s is already loaded", name)
            return
        loader(self, "plugin", name)

    def load_dict(self, data: DeclarationDict):
        """Load declarations from dictionary.
        """
        loader(self, "dict", data)

    def into_ini(
            self,
            minimal: bool,
            include_docs: bool = False,
            section: str = "app:main"
    ) -> str:
        """Serialize declaration into config template.
        """
        return serializer(self, "ini", minimal, include_docs, section)

    def into_schema(self) -> Dict[str, Any]:
        """Serialize declaration into validation schema.
        """
        return serializer(self, "validation_schema")

    def into_docs(self) -> str:
        """Serialize declaration into reST documentation.
        """
        return serializer(self, "rst")

    def describe(self, fmt: str) -> str:
        """Describe definition of options in the given format.
        """
        return describer(self, fmt)

    def declare(
        self, key: Union[Key, str], default: Optional[T] = None
    ) -> Option[T]:
        """Add declaration of the option with the given default value.
        """
        return self.declare_option(key, Option(default))

    def declare_option(
        self, key: Union[Key, str], option: Option[T]
    ) -> Option[T]:
        """Add the declaration using existing Option object.

        Use this method for declaring options using Option subclasses.
        """
        if self._sealed:
            raise TypeError("Sealed declaration cannot be updated")

        if isinstance(key, str):
            key = Key.from_string(key)

        if key in self._options:
            raise ValueError(f"{key} already declared")
        self._members.append(key)

        self._options[key] = option
        return option

    def declare_bool(
            self, key: Key, default: Optional[bool] = False) -> Option[bool]:
        """Declare boolean option.
        """
        option = self.declare(key, bool(default))
        option.set_validators("boolean_validator")
        return option

    def declare_int(self, key: Key, default: Optional[int]) -> Option[int]:
        """Declare numeric option.
        """
        option = self.declare(key, default)
        option.set_validators("convert_int")
        return option

    def declare_list(
            self, key: Key, default: Optional[list[Any]]) -> Option[list[Any]]:
        """Declare option that accepts space-separated list of values.
        """
        option = self.declare(key, default)
        option.set_validators("as_list")
        return option

    def declare_dynamic(self, key: Key, default: Any = None) -> Option[Any]:
        """Declare dynamic option using a Key with `<name>` segment(surrounded
        with angles).

        """
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

    def annotate(self, text: str) -> Annotation:
        """Add section annotation.

        All the options added after this call(and till the next annotation)
        will be grouped into separate config section.

        Sections only affect documentation/config template. They do not modify
        CKAN behavior and are not reflected inside the `config` object.

        """
        if self._sealed:
            raise TypeError("Sealed declaration cannot be updated")

        annotation = Annotation(text)
        self._members.append(annotation)
        return annotation
