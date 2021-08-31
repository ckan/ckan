# -*- coding: utf-8 -*-
from __future__ import annotations

import textwrap
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    NewType,
    Optional,
    OrderedDict,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

T = TypeVar("T")

ConverterFrom = Callable[[str], T]
ConverterInto = Callable[[T], str]

UnsetType = NewType("UnsetType", dict)

UNSET = UnsetType({})
DefaultType = Union[T, UnsetType]


class Option:
    __path: Tuple[str, ...]

    def __init__(self, path: Sequence[str] = ()):
        self.__path = tuple(path)

    def __str__(self):
        return ".".join(self.__path)

    def __len__(self):
        return len(self.__path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: Any):
        if isinstance(other, str):
            return str(self) == other

        elif isinstance(other, Option):
            return self.__path == other.__path

        return super().__eq__(other)

    def __getitem__(self, idx):
        return self.__path[idx]

    def __getattr__(self, fragment: str):
        return self._descend(fragment)

    def _descend(self, fragment) -> Option:
        return Option(self.__path + (fragment,))

    def _ascend(self) -> Option:
        return Option(self.__path[:-1])

    def _behead(self) -> Tuple[str, Option]:
        head, *tail = self.__path
        return head, Option(tail)

    def _split(self) -> Tuple[Option, str]:
        *head, tail = self.__path
        return Option(head), tail

    @staticmethod
    def from_string(path: str):
        return Option([fragment for fragment in path.split(".") if fragment])


class Details(Generic[T]):
    default: DefaultType[T]
    commented: bool = False
    description: Optional[str] = None

    def __init__(self, default: DefaultType[T] = UNSET):
        self.default = default

    def __str__(self):
        if self.has_default():
            return str(self.default)
        return ""

    def has_default(self):
        return self.default is not UNSET

    def set_description(self, description: str):
        self.description = description
        return self

    def set_default(self, default: T):
        self.default = default
        return self

    def comment(self):
        self.commented = True
        return self


class Annotation(str):
    pass


class Declaration:
    _global: ClassVar[Declaration]
    _mapping: dict[Option, Details]
    _order: list[Union[Option, Annotation]]

    @classmethod
    def set_global(cls, declaration: Declaration):
        cls._global = declaration
        return declaration

    @classmethod
    def get_global(cls):
        if not hasattr(cls, "_global"):
            cls.set_global(cls())
        return cls._global

    def __init__(self):
        self._mapping = OrderedDict()
        self._order = []

    def __getitem__(self, option: Option) -> Details:
        return self._mapping[option]

    def __str__(self):
        result = ""
        for item in self._order:
            if isinstance(item, Option):
                value = self._mapping[item]
                if value.description:
                    result += (
                        textwrap.fill(
                            value.description,
                            initial_indent="# ",
                            subsequent_indent="# ",
                        )
                        + "\n"
                    )

                result += "{comment}{key} = {value}\n".format(
                    comment="# " if value.commented else "",
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

    def declare(
        self, option: Option, default: DefaultType[T] = UNSET
    ) -> Details[T]:
        value = Details(default)
        if option not in self._mapping:
            self._order.append(option)

        self._mapping[option] = value
        return value

    def annotate(self, annotation: str):
        self._order.append(Annotation(annotation))
