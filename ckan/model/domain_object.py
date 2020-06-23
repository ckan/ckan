# encoding: utf-8

import datetime
import six
from collections import OrderedDict

import sqlalchemy as sa
from sqlalchemy import orm
from six import string_types

from ckan.model import meta, core


__all__ = ['DomainObject', 'DomainObjectOperation']


class Enum(set):
    '''Simple enumeration
    e.g. Animal = Enum("dog", "cat", "horse")
    joey = Animal.DOG
    '''
    def __init__(self, *names):
        super(Enum, self).__init__(names)

    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError

DomainObjectOperation = Enum('new', 'changed', 'deleted')

class DomainObject(object):

    text_search_fields = []
    Session = meta.Session

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def count(cls):
        return cls.Session.query(cls).count()

    @classmethod
    def by_name(cls, name, autoflush=True, for_update=False):
        q = meta.Session.query(cls).autoflush(autoflush
            ).filter_by(name=name)
        if for_update:
            q = q.with_for_update()
        return q.first()

    @classmethod
    def text_search(cls, query, term):
        register = cls
        make_like = lambda x,y: x.ilike('%' + y + '%')
        q = None
        for field in cls.text_search_fields:
            attr = getattr(register, field)
            q = sa.or_(q, make_like(attr, term))
        return query.filter(q)

    @classmethod
    def active(cls):
        return meta.Session.query(cls).filter_by(state=core.State.ACTIVE)

    def save(self):
        self.add()
        self.commit()

    def add(self):
        self.Session.add(self)

    def commit_remove(self):
        self.commit()
        self.remove()

    def commit(self):
        self.Session.commit()

    def remove(self):
        self.Session.remove()

    def delete(self):
        # stateful objects have this method overridden - see
        # core.StatefulObjectMixin
        self.Session.delete(self)

    def purge(self):
        self.Session().autoflush = False
        self.Session.delete(self)

    def as_dict(self):
        """
        returns: ordered dict with fields from table. Date/time values
        are converted to strings for json compatibilty
        """
        _dict = OrderedDict()
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            val = getattr(self, col.name)
            if isinstance(val, datetime.date):
                val = str(val)
            if isinstance(val, datetime.datetime):
                val = val.isoformat()
            _dict[col.name] = val
        return _dict

    def from_dict(self, _dict):
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
        changed = set()
        skipped = dict(_dict)
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            if col.name.startswith('_'):
                continue
            if col.name in _dict:
                value = _dict[col.name]
                db_value = getattr(self, col.name)
                if isinstance(db_value, datetime.datetime) and isinstance(value, string_types):
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

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return repr(self)

    def __unicode__(self):
        repr = u'<%s' % self.__class__.__name__
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            try:
                repr += u' %s=%s' % (col.name, getattr(self, col.name))
            except Exception as inst:
                repr += u' %s=%s' % (col.name, inst)

        repr += '>'
        return repr

    def __repr__(self):
        return six.ensure_str(self.__unicode__())
