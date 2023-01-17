# -*- coding: utf-8 -*-
"""This module defines the ways to serialize the config declaration into
different structures, such as: documentation string, config template,
validation schema.

New serializers can be defined in the following manner:

```python
from ckan.config.declaration.serialize import handler, serializer

@handler.register("custom-format")
def serialize_into_custom(declaration, *args, **kwargs):
    ...

## and now new `custom-format` can be used like this:
serialized_declaration = serializer(
    declaration, "custom-format", *args, **kwargs)
```

This mechanism allows you to re-define default serializers, though it should be
avoided unless you have an irresistible desire to hack into CKAN core.

"""
import os
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict

import ckan

from .key import Key, Pattern
from .option import Flag, Annotation
from .utils import FormatHandler

if TYPE_CHECKING:
    from . import Declaration


log = logging.getLogger(__name__)
handler: FormatHandler[Callable[..., Any]] = FormatHandler()
serializer = handler.handle


@handler.register("ini")
def serialize_ini(
    declaration: "Declaration", minimal: bool, include_docs: bool, section: str
):
    """Serialize declaration into config template.

    Output:
        ## Section #######
        ## doc string in `include_docs` mode
        option.name = option-value
        another.option =

    Args:
        minimal: include only required options.
            Skip section dividers and all the options with default value
        include_docs: include description of the option into output.
    """
    result = ""

    for item in declaration._members:

        if isinstance(item, Annotation):
            if item._section != section:
                continue

            if minimal:
                continue

            heading = f"## {item} #".ljust(80, "#")
            result += f"\n{heading}\n"

        elif isinstance(item, Key):
            option = declaration._options[item]

            if option._section != section:
                continue

            if option.has_flag(Flag.non_iterable()):
                continue

            if minimal and not option.has_flag(Flag.required):
                # minimal config template relies on default values.
                continue

            if option.description and include_docs:
                result += "\n".join(
                    "## " + line for line in option.description.splitlines()
                ) + "\n"

            if not option.has_default():
                value = option.placeholder or ""
            elif isinstance(option.default, bool):
                value = option.str_value().lower()
            else:
                value = option.str_value()

            if option.has_flag(Flag.commented):
                result += "# "

            if isinstance(item, Pattern):
                # Patterns are not actual config options, but rather an example
                # of possibilities: `sqlalchemy.<option> = `. Thus they cannot
                # be added to config file as real options. But still, we want
                # to show user, that he can use patterns as well.
                result += "# "

            result += f"{item} = {value}\n"

    return result


@handler.register("validation_schema")
def serialize_validation_schema(declaration: "Declaration") -> Dict[str, Any]:
    """Serialize declaration into validation schema.
    """
    return {
        str(key): option._parse_validators()
        for key, option in declaration._options.items()
    }


@handler.register("rst")
def serialize_rst(declaration: "Declaration"):
    """Serialize declaration into reST documentation.
    """
    result = ""

    # Config option may refer to the absolute filepath in their default
    # values. One of such options is `ckan.resource_formats`. Just to avoid
    # misunderstanding, we'll update these options, replacing the path till
    # CKAN root with `/<CKAN_ROOT>` segment.
    ckan_root = os.path.dirname(
        os.path.dirname(os.path.realpath(ckan.__file__)))

    for item in declaration._members:
        if isinstance(item, Annotation):
            result += ".. _{anchor}:\n\n{header}\n{divider}\n\n".format(
                anchor=item.lower().replace(' ', '-'),
                header=item,
                divider=len(item) * "-"
            )

        elif isinstance(item, Key):
            option = declaration._options[item]
            if option.has_flag(Flag.non_iterable()):
                continue
            if not option.description:
                log.warning(
                    "Skip %s option because it has no description",
                    item
                )
                continue

            result += ".. _{anchor}:\n\n{option}\n{divider}\n".format(
                anchor=item, option=item, divider=len(str(item)) * '^'
            )

            if option.example:
                result += f"Example::\n\n\t{item} = {option.example}\n\n"

            default = option.str_value()

            if default != '':
                if default.startswith(ckan_root):
                    default = default.replace(ckan_root, '/<CKAN_ROOT>')
                default = f"``{default}``"
            else:
                default = "none"

            result += f"Default value: {default}\n\n"
            result += option.description + "\n\n"

    return result
