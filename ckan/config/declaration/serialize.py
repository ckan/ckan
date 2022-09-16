# -*- coding: utf-8 -*-

import os
from typing import TYPE_CHECKING, Any, Callable, Dict

import ckan

from .key import Key, Pattern
from .option import Flag, Annotation
from .utils import FormatHandler

if TYPE_CHECKING:
    from . import Declaration

handler: FormatHandler[Callable[..., Any]] = FormatHandler()
serializer = handler.handle


@handler.register("ini")
def serialize_ini(
    declaration: "Declaration", minimal: bool, verbose: bool
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
            if option.description and verbose:
                result += "\n".join(
                    "## " + line for line in option.description.splitlines()
                ) + "\n"
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


@handler.register("rst")
def serialize_rst(declaration: "Declaration"):
    result = ""
    ckan_root = os.path.dirname(
        os.path.dirname(os.path.realpath(ckan.__file__)))

    for item in declaration._order:
        if isinstance(item, Annotation):

            result += ".. _{}:\n\n{}\n{}\n\n".format(
                item.lower().replace(' ', '-'), item, len(item) * "-")

        elif isinstance(item, Key):
            option = declaration._mapping[item]
            if option._has_flag(Flag.non_iterable()):
                continue
            if not option.description:
                continue

            result += ".. _{}:\n\n{}\n{}\n".format(
                item, item, len(str(item)) * '^')

            if option.example:
                result += f"Example::\n\n\t{item} = {option.example}\n\n"

            default = str(option) if option.has_default() else ''

            if default != '':
                if default.startswith(ckan_root):
                    default = default.replace(ckan_root, '/<CKAN_ROOT>')
                default = f"``{default}``"
            else:
                default = "none"
            result += f"Default value: {default}\n\n"

            result += option.description + "\n\n"

    return result
