# -*- coding: utf-8 -*-
"""This module defines the ways to fill config declaration with difinitions
from different sources.

New loaders can be defined in the following manner:

```python
from ckan.config.declaration.load import handler, loader

@handler.register("custom-format")
def load_from_custom(declaration, *args, **kwargs):
    ...

## and now new `custom-format` can be used like this:
loader(declaration, "custom-format", *args, **kwargs)
```

This mechanism allows you to re-define default loaders, though it should be
avoided unless you have an irresistible desire to hack into CKAN core.

"""
from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, Any, Callable, Dict, List
from typing_extensions import TypedDict
import yaml

from .key import Key
from .option import Flag, Option
from .utils import FormatHandler

if TYPE_CHECKING:
    from . import Declaration


log = logging.getLogger(__name__)

option_types = {
    "base": "declare",
    "bool": "declare_bool",
    "int": "declare_int",
    "dynamic": "declare_dynamic",
    "list": "declare_list",
}

handler: FormatHandler[Callable[..., None]] = FormatHandler()
loader = handler.handle


class OptionV1(TypedDict, total=False):
    key: str

    default: Any
    default_callable: str
    placeholder_callable: str
    callable_args: Dict[str, Any]

    description: str

    validators: str
    type: str


class GroupV1(TypedDict):
    annotation: str
    section: str
    options: List[OptionV1]


class DeclarationDictV1(TypedDict):
    version: int
    groups: List[GroupV1]


DeclarationDict = DeclarationDictV1


@handler.register("plugin")
def load_plugin(declaration: "Declaration", name: str):
    """Load declarations from CKAN plugin.
    """
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

    plugin.declare_config_options(declaration, Key())


@handler.register("dict")
def load_dict(declaration: "Declaration", definition: DeclarationDict):
    """Load declarations from dictionary.
    """
    from ckan.logic.schema import config_declaration_v1
    from ckan.logic import ValidationError
    from ckan.lib.navl.dictization_functions import validate

    version = definition["version"]
    if version == 1:
        data, errors = validate(dict(definition), config_declaration_v1())
        if errors:
            raise ValidationError(errors)

        for group in data["groups"]:
            if group["annotation"]:
                declaration.annotate(group["annotation"]).set_section(
                    group["section"]
                )

            for details in group["options"]:
                factory = option_types[details["type"]]
                option: Option[Any] = getattr(declaration, factory)(
                    details["key"], details.get("default")
                )
                option.set_section(group["section"])
                option.append_validators(details["validators"])
                option.legacy_key = details.get("legacy_key")

                extras = details.setdefault("__extras", {})
                for flag in Flag:
                    if extras.get(flag.name):
                        option.set_flag(flag)

                if details["description"]:
                    option.set_description(details["description"])

                if details["placeholder"]:
                    option.set_placeholder(details["placeholder"])

                if "example" in details:
                    option.example = details["example"]

                if "default_callable" in details:
                    args = details.get("callable_args", {})
                    default = details["default_callable"](**args)
                    option.set_default(default)

                if "placeholder_callable" in details:
                    args = details.get("callable_args", {})
                    placeholder = details["placeholder_callable"](**args)
                    option.set_placeholder(placeholder)


@handler.register("core")
def load_core(declaration: "Declaration"):
    """Load core declarations.
    """
    source = pathlib.Path(__file__).parent / ".." / "config_declaration.yaml"
    with source.open("r") as stream:
        data = yaml.safe_load(stream)
        load_dict(declaration, data)
