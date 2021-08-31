# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import (
    Any, Callable, ClassVar, Generic, NewType, Optional, OrderedDict,
    Sequence, Tuple, TypeVar, Union
)

T = TypeVar("T")

ConverterFrom = Callable[[str], T]
ConverterInto = Callable[[T], str]

UnsetType = NewType("UnsetType", dict)

UNSET = UnsetType({})
DefaultType = Union[T, UnsetType]


def _identity(v: Any):
    return v


class Option:
    __path: Tuple[str, ...]

    def __init__(self, path: Sequence[str]=()):
        self.__path = tuple(path)

    def __str__(self):
        return ".".join(self.__path)

    def __bool__(self):
        return len(self.__path) > 0

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: Any):
        if isinstance(other, str):
            return str(self) == other

        elif isinstance(other, Option):
            return self.__path == other.__path

        return super().__eq__(other)

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
    description: Optional[str] = None

    from_str: ConverterFrom = _identity
    into_str: ConverterInto = str


    def __init__(self, default: DefaultType[T] = UNSET):
        self.default = default

    def has_default(self):
        return self.default is not UNSET

    def use_converters(self, from_: ConverterFrom, into_: ConverterInto):
        if from_:
            self.from_str = from_
        if into_:
            self.into_str = into_
        return self

    def set_description(self, description: str):
        self.description = description


class Declaration:
    _global: ClassVar[Declaration]
    _mapping: OrderedDict[str, Union[Details, Declaration]]

    @classmethod
    def set_global(cls, declaration: Declaration):
        cls._global = declaration
        return declaration

    @classmethod
    def get_global(cls):
        return cls._global

    def __init__(self, initial = {}):
        self._mapping = OrderedDict(initial)

    def __getitem__(self, option: Option) -> Union[Details, Declaration]:
        section_key, value_key = option._split()
        section = self.get_section(section_key)
        return section._mapping[value_key]

    def get_section(self, option: Option,
                    create_missing: bool = False) -> Declaration:
        if not option:
            # whole declaration requested via Option()
            return self

        section = self._mapping
        tail = option
        while True:
            head, tail = tail._behead()

            if head not in section and create_missing:
                section[head] = Declaration()
            else:
                raise KeyError(option)

            child = section[head]
            if not isinstance(child, Declaration):
                raise ValueError(
                    f"Unexpected value at {option}[{head} segment]."
                )

            if not tail:
                break
            section = child._mapping

        return child

    def declare(self, option: Option, value: Details):
        section_key, value_key = option._split()
        section = self.get_section(section_key, create_missing=True)

        section._mapping[value_key] = value
