# -*- coding: utf-8 -*-
"""This module defines the ways to fill config declaration with definitions
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
import msgspec

from ckan import types
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
    """Load declarations from CKAN plugin."""
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
    """Load declarations from dictionary."""
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
                declaration.annotate(group["annotation"]).set_section(group["section"])

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
    """Load core declarations."""
    source = pathlib.Path(__file__).parent / ".." / "config_declaration.yaml"
    with source.open("rb") as stream:
        data = msgspec.yaml.decode(stream.read())
        load_dict(declaration, data)


@handler.register("files")
def load_files(declaration: "Declaration", /, config: Any = None):
    """Generate declarations for configured storages.

    Every uniques storage in the config will produce declarations depending on
    its type. These declarations will be used to discover possible
    configuration and validate settings specific for the selected storage
    adapter.
    """
    from ckan.common import config as default_config
    from ckan.lib import files

    if config is None:
        config = default_config

    storages = config_tree(config, files.STORAGE_PREFIX, depth=1)

    # add config declarations for configured storages. In this way user can
    # print all available options for every storage via `ckan config
    # declaration --core`
    for name, settings in storages.items():
        # make base key so that storage can declare options by extending. I.e.,
        # `storage_key.option_name`, instead of logner form
        # `key.ckanext.files.storage.STORAGE_NAME.option_name`
        storage_key = Key().from_string(files.STORAGE_PREFIX + name)

        available_adapters = msgspec.json.encode(
            [item for item in files.adapters if not files.adapters[item].hidden],
        ).decode()

        # this option reports unrecognized type of the storage and shows all
        # available correct types
        declaration.declare(
            storage_key.type,
            settings.get("type"),
        ).append_validators(
            f"one_of({available_adapters})",
        ).set_description(
            "Adapter used by the storage",
        ).required()

        # obviously, adapter must be specified. But at this point validation
        # hasn't happened yet, and settings can include anything. If `type` is
        # missing, it will be reported after the validation.
        adapter = files.adapters.get(settings.get("type", ""))
        if not adapter or not issubclass(adapter, files.Storage):
            continue

        adapter.declare_config_options(declaration, storage_key)


def config_tree(
    config: types.CKANConfig,
    prefix: str = "",
    depth: int = 0,
    keep_prefix: bool = False,
) -> dict[str, Any]:
    """Extract subtree from configuration.

    Select config options that match the prefix and split options by ``.``
    character, transform result into nested dictionary. The maximum depth
    of the result is controlled by ``depth`` argument. Option `a.b.c = 1`
    transforms into ``{"a.b.c": 1}`` with depth 0, ``{"a": {"b.c": 1}}``
    with depth 1, ``{"a": {"b": {"c": 1}}}`` with depth 2, etc.

    Examples::

        >>> cfg = CKANConfig({
        >>>     "a.b.c": 1,
        >>>     "a.b.d": 2,
        >>>     "x.y.z": 3,
        >>>     "x.x.x": 4,
        >>> })
        >>>
        >>> assert config_tree(cfg, "a.b.") == {"c": 1, "d": 2}
        >>> assert config_tree(cfg, "x.", depth=1) == {"x": {"y.z": 3, "x.x": 4}}
        >>> assert config_tree(cfg, "x.x", keep_prefix=True) == {"x.x.x": 4}

    :param prefix: common prefix for selected options
    :param depth: branch depth for extracted configuration

    :returns: extracted configuration

    """
    result = {}
    strip_len = 0 if keep_prefix else len(prefix)

    for k, v in config.items():
        if not k.startswith(prefix):
            continue

        path = k[strip_len:].split(".", depth)
        if not path:
            continue

        here = result
        for segment in path[:-1]:
            here = here.setdefault(segment, {})
            if not isinstance(here, dict):
                log.warning(
                    "Cannot build tree for %s at branch %s",
                    path,
                    segment,
                )
                break
        else:
            here[path[-1]] = v

    return result
