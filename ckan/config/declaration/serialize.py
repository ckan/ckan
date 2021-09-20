# -*- coding: utf-8 -*-

import textwrap
from typing import TYPE_CHECKING, Any, Callable, Dict


from .key import Key
from .option import Flag, Annotation
from .utils import FormatHandler

if TYPE_CHECKING:
    from . import Declaration

handler: FormatHandler[Callable[["Declaration"], Any]] = FormatHandler()
serialize = handler.handle


@handler.register("ini")
def serialize_ini(declaration: "Declaration"):
    result = ""
    for item in declaration._order:
        if isinstance(item, Key):
            option = declaration._mapping[item]
            if option._has_flag(Flag.non_iterable()):
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


@handler.register("validation_schema")
def serialize_validation_schema(declaration: "Declaration") -> Dict[str, Any]:
    schema = {}
    for key, option in declaration._mapping.items():
        schema[str(key)] = _validators_from_string(option.get_validators())

    return schema


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
