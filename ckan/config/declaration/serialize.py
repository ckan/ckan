# -*- coding: utf-8 -*-

import textwrap
from typing import TYPE_CHECKING, Any, Callable, Dict


from .key import Key, Pattern
from .option import Flag, Annotation
from .utils import FormatHandler

if TYPE_CHECKING:
    from . import Declaration

handler: FormatHandler[Callable[..., Any]] = FormatHandler()
serialize = handler.handle


@handler.register("ini")
def serialize_ini(
    declaration: "Declaration", minimal: bool, no_comments: bool
):
    result = ""
    for item in declaration._order:
        if isinstance(item, Key):
            option = declaration._mapping[item]
            if option._has_flag(Flag.non_iterable()):
                continue
            if minimal and not option._has_flag(Flag.required):
                if item == "config.mode":
                    result += "config.mode = strict\n"
                continue
            if option.description and not no_comments:
                result += (
                    textwrap.fill(
                        option.description,
                        initial_indent="## ",
                        subsequent_indent="## ",
                    )
                    + "\n"
                )

            if not option.has_default():
                value = option.placeholder or ""
            elif isinstance(option.default, bool):
                value = str(option).lower()
            else:
                value = str(option)

            if isinstance(item, Pattern):
                result += "# "
            result += f"{item} = {value}\n"

        elif isinstance(item, Annotation):
            if minimal:
                continue
            result += "\n{}\n".format(f"## {item} #".ljust(80, "#"))

    return result


@handler.register("validation_schema")
def serialize_validation_schema(declaration: "Declaration") -> Dict[str, Any]:
    schema = {}
    for key, option in declaration._mapping.items():
        schema[str(key)] = option._parse_validators()

    return schema
