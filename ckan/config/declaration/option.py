# -*- coding: utf-8 -*-

import enum
from typing import Any, Generic, Optional, TypeVar


T = TypeVar("T")


class UnsetType(dict):
    def __repr__(self):
        return ""


class Flag(enum.Flag):
    ignored = enum.auto()
    experimental = enum.auto()
    internal = enum.auto()

    @classmethod
    def none(cls):
        return cls(0)

    @classmethod
    def non_iterable(cls):
        return cls.ignored | cls.experimental | cls.internal

    @classmethod
    def not_safe(cls):
        return cls.ignored | cls.internal


class Annotation(str):
    pass


class Option(Generic[T]):
    __slots__ = ("flags", "default", "description", "_validators")

    flags: Flag
    default: Optional[T]
    description: Optional[str]
    _validators: str

    def __init__(self, default: Optional[T] = None):
        self.flags = Flag.none()
        self.description = None
        self._validators = ""
        self.default = default

    def __str__(self):
        return str(self.default)

    def _unset_flag(self, flag: Flag):
        self.flags &= ~flag

    def _set_flag(self, flag: Flag):
        self.flags |= flag

    def _has_flag(self, flag: Flag) -> bool:
        return bool(self.flags & flag)

    def has_default(self):
        return self.default is not None

    def set_default(self, default: T):
        self.default = default
        return self

    def set_description(self, description: str):
        self.description = description
        return self

    def set_validators(self, validators: str):
        self._validators = validators
        return self

    def append_validators(self, validators: str):
        if validators:
            self._validators += " " + validators

    def get_validators(self):
        return self._validators

    def ignore(self):
        self._set_flag(Flag.ignored)

    def experimental(self):
        self._set_flag(Flag.experimental)

    def internal(self):
        self._set_flag(Flag.internal)

    def _normalize(self, value: Any):
        from ckan.lib.navl.dictization_functions import validate

        data, _ = validate(
            {"value": value}, {"value": self._parse_validators()}
        )
        return data["value"]

    def _parse_validators(self):
        return _validators_from_string(self.get_validators())


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
