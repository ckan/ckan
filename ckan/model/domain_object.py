# encoding: utf-8
from __future__ import annotations

from typing import Any, Set, TypeVar

from typing_extensions import Self

import ckan.model.core as core
from ckan.types import Query

from .base import (
    ActiveRecordMixin,
    TextSearchMixin,
    DictMixin,
    NameMixin,
    DebugMixin,
)

T = TypeVar("T")

__all__ = ['DomainObject', 'DomainObjectOperation']

class Enum(Set[T]):
    '''Simple enumeration
    e.g. Animal = Enum("dog", "cat", "horse")
    joey = Animal.dog
    '''
    def __init__(self, *names: T) -> None:
        super(Enum, self).__init__(names)

    def __getattr__(self, name: Any) -> T:
        if name in self:
            return name
        raise AttributeError

DomainObjectOperation = Enum('new', 'changed', 'deleted')

class DomainObject(
        ActiveRecordMixin, DictMixin, NameMixin, TextSearchMixin, DebugMixin):

    def __init__(self, **kwargs: Any) -> None:
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def count(cls) -> int:
        return cls.Session.query(cls).count()

    @classmethod
    def active(cls) -> Query[Self]:
        return cls.Session.query(cls).filter_by(state=core.State.ACTIVE)
