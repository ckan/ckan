# encoding: utf-8
from __future__ import annotations

import datetime
from collections import OrderedDict
from typing import Any, Callable, Optional, Set, Type, TypeVar

import sqlalchemy as sa
from sqlalchemy import orm


import ckan.model.meta as meta
import ckan.model.core as core
from ckan.types import Query


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

class DomainObject(object):
    name: str

    text_search_fields: list[str] = []
    Session = meta.Session

    def __init__(self, **kwargs: Any) -> None:
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def count(cls) -> int:
        return cls.Session.query(cls).count()

    @classmethod
    def by_name(cls: Type[T], name: Optional[str], autoflush: bool=True,
                for_update: bool=False) -> Optional[T]:
        q = meta.Session.query(cls).autoflush(autoflush
            ).filter_by(name=name)
        if for_update:
            q = q.with_for_update()
        return q.first()

    @classmethod
    def text_search(cls, query: Any, term: str) -> Any:
        register = cls
        make_like: Callable[
            [Any, str], str] = lambda x, y: x.ilike('%' + y + '%')
        q: Any = sa.null() | sa.null()
        for field in cls.text_search_fields:
            attr = getattr(register, field)
            q = sa.or_(q, make_like(attr, term))
        return query.filter(q)

    @classmethod
    def active(cls: Type[T]) -> 'Query[T]':
        return meta.Session.query(cls).filter_by(state=core.State.ACTIVE)

    def save(self) -> None:
        self.add()
        self.commit()

    def add(self) -> None:
        self.Session.add(self)

    def commit_remove(self) -> None:
        self.commit()
        self.remove()

    def commit(self) -> None:
        self.Session.commit()

    def remove(self) -> None:
        self.Session.remove()

    def delete(self) -> None:
        # stateful objects have this method overridden - see
        # core.StatefulObjectMixin
        self.Session.delete(self)

    def purge(self) -> None:
        self.Session().autoflush = False
        self.Session.delete(self)

    def as_dict(self) -> dict[str, Any]:
        """
        returns: ordered dict with fields from table. Date/time values
        are converted to strings for json compatibilty
        """
        _dict: dict[str, Any] = OrderedDict()
        table: Any = orm.class_mapper(self.__class__).persist_selectable
        for col in table.c:
            val = getattr(self, col.name)
            if isinstance(val, datetime.date):
                val = str(val)
            if isinstance(val, datetime.datetime):
                val = val.isoformat()
            _dict[col.name] = val
        return _dict

    def from_dict(self,
                  _dict: dict[str, Any]) -> tuple[set[Any], dict[str, Any]]:
        """
        Loads data from dict into table.

        Returns (changed, skipped) tuple. changed is a set of keys
        that were different than the original values, i.e. changed
        is an empty list when no values were changed by this call.
        skipped is a dict containing any items from _dict whose keys
        were not found in columns.

        When key for a column is not present in _dict, columns marked
        with doc='remove_if_not_provided' will have their field set
        to N , otherwise existing field value won't be changed.
        """
        changed: set[Any] = set()
        skipped = dict(_dict)
        table: Any = orm.class_mapper(self.__class__).persist_selectable
        for col in table.c:
            if col.name.startswith('_'):
                continue
            if col.name in _dict:
                value = _dict[col.name]
                db_value = getattr(self, col.name)
                if isinstance(db_value, datetime.datetime) and isinstance(value, str):
                    db_value = db_value.isoformat()
                if db_value != value:
                    changed.add(col.name)
                    setattr(self, col.name, value)
                del skipped[col.name]
            elif col.doc == 'remove_if_not_provided':
                blank = None if col.nullable else ''
                # these are expected when updating, clear when missing
                if getattr(self, col.name) != blank:
                    changed.add(col.name)
                    setattr(self, col.name, blank)
        return changed, skipped

    def __lt__(self, other: 'DomainObject') -> bool:
        return self.name < other.name

    def __repr__(self):
        repr = u'<%s' % self.__class__.__name__
        table: Any = orm.class_mapper(self.__class__).persist_selectable
        for col in table.c:
            try:
                repr += u' %s=%s' % (col.name, getattr(self, col.name))
            except Exception as inst:
                repr += u' %s=%s' % (col.name, inst)

        repr += '>'
        return repr
