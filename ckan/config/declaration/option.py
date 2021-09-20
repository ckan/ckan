# -*- coding: utf-8 -*-

import enum
from typing import Generic, Optional, TypeVar, Union


T = TypeVar("T")


class UnsetType(dict):
    def __repr__(self):
        return ""


UNSET = UnsetType()
DefaultType = Union[T, UnsetType]


class Flag(enum.Flag):
    disabled = enum.auto()
    ignored = enum.auto()
    experimental = enum.auto()
    internal = enum.auto()
    no_default = enum.auto()

    @classmethod
    def none(cls):
        return cls(0)

    @classmethod
    def non_iterable(cls):
        return cls.ignored | cls.experimental | cls.internal


class Annotation(str):
    pass


class Option(Generic[T]):
    __slots__ = ("flags", "default", "description", "_validators")

    flags: Flag
    default: DefaultType[T]
    description: Optional[str]
    _validators: str

    def __init__(self, default: DefaultType[T] = UNSET):
        self.flags = Flag.none()
        self.description = None
        self._validators = ""

        self.default = default
        if default is UNSET:
            self._set_flag(Flag.no_default)

    def __str__(self):
        return str(self.default)

    def _unset_flag(self, flag: Flag):
        self.flags &= ~flag

    def _set_flag(self, flag: Flag):
        self.flags |= flag

    def _has_flag(self, flag: Flag) -> bool:
        return bool(self.flags & flag)

    def has_default(self):
        return not self._has_flag(Flag.no_default)

    def set_default(self, default: T):
        self.default = default
        self._unset_flag(Flag.no_default)
        return self

    def set_description(self, description: str):
        self.description = description
        return self

    def set_validators(self, validators: str):
        self._validators = validators

    def append_validators(self, validators: str):
        self._validators += " " + validators

    def get_validators(self):
        return self._validators

    def disable(self):
        self._set_flag(Flag.disabled)

    def ignore(self):
        self._set_flag(Flag.ignored)

    def experimental(self):
        self._set_flag(Flag.experimental)

    def internal(self):
        self._set_flag(Flag.internal)
