# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
from collections import OrderedDict
from typing import Any, Callable, Optional

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from typing_extensions import Self

from .meta import metadata, Session

BaseModel = declarative_base(metadata=metadata)


class SessionMixin:
    """Attach session to the model class.

    Example:
        class MyModel(SessionMixin, Base):
            ...
            @classmethod
            def count(cls):
                return cls.Session.query(cls).count()

    """
    Session = Session


class DebugMixin:
    """Defines __repr__ method that shows all the model's columns.

    Example:
        class MyModel(DebugMixin, Base):
            name: str
            ...

        >>> MyModel(name="hello world")
        <MyModel name=hello world>
    """

    def __repr__(self):
        """Show model name and all the columns with their values.
        """
        output = u'<%s' % self.__class__.__name__
        table: Any = orm.class_mapper(self.__class__).persist_selectable
        for col in table.c:
            try:
                output += u' %s=%s' % (col.name, getattr(self, col.name))
            except Exception as inst:
                output += u' %s=%s' % (col.name, inst)

        output += '>'
        return output


class NameMixin(SessionMixin):
    """Add search and sorting by name to a model with `name` column.

    Example:
        class MyModel(NameMixin, Base):
            name: str
            ...

        >>> MyModel.by_name("hello world")
        None

        >>> MyModel(name="hello world")
        >>> MyModel.by_name("hello world")
        <MyModel name=hello world>

        >>> a_obj = MyModel(name="A")
        >>> d_obj = MyModel(name="D")
        >>> assert a_obj < d_obj
    """

    name: str

    def __lt__(self, other: Self) -> bool:
        return self.name < other.name

    @classmethod
    def by_name(
            cls, name: Optional[str], autoflush: bool = True,
            for_update: bool = False) -> Optional[Self]:
        """Return first record with the given name.
        """
        q = cls.Session.query(cls).autoflush(autoflush).filter_by(name=name)
        if for_update:
            q = q.with_for_update()

        return q.first()


class TextSearchMixin:
    """Provide base text-search functionality via LIKE SQL operator.

    Text-search uses columns specified by `text_search_fields` property.

    Example:
        class MyModel(TextSearchMixin, Base):
            text_search_fields = ["name"]
            name: str
            ...

        >>> MyModel(name="hello world")
        >>> q = model.Session.query(MyModel)
        >>> MyModel.text_search(q, "llo").all()
        [<MyModel name=hello world>]
    """
    text_search_fields: list[str] = []

    @classmethod
    def text_search(cls, query: Any, term: str) -> Any:
        """Add ILIKE filters to the query.
        """
        register = cls
        make_like: Callable[
            [Any, str], str] = lambda x, y: x.ilike('%' + y + '%')
        q: Any = sa.null() | sa.null()
        for field in cls.text_search_fields:
            attr = getattr(register, field)
            q = sa.or_(q, make_like(attr, term))
        return query.filter(q)


class ActiveRecordMixin(SessionMixin):
    """Provides shortcuts for entity lifecycle management.
    """
    def save(self) -> None:
        """Write entity to DB.
        """
        self.add()
        self.commit()

    def add(self) -> None:
        """Add entity to the session, but don't commit the transaction.
        """
        self.Session.add(self)

    def commit_remove(self) -> None:
        """Commit the transaction and dispose the Session.
        """
        self.commit()
        self.remove()

    def commit(self) -> None:
        """Commit the transaction.
        """
        self.Session.commit()

    def remove(self) -> None:
        """Dispose the Session.
        """
        self.Session.remove()

    def delete(self) -> None:
        """Mark an instance as deleted.
        """
        # stateful objects have this method overridden - see
        # core.StatefulObjectMixin
        self.Session.delete(self)

    def purge(self) -> None:
        """Mark an instance as deleted.
        """
        self.Session().autoflush = False
        self.Session.delete(self)


class DictMixin:
    """Provides helpers for dict-model conversion.
    """
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
                if isinstance(db_value, datetime.datetime) and isinstance(
                        value, str):
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
