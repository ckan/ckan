import datetime

from sqlalchemy.util import OrderedDict

from meta import *

# TODO: replace this (or at least inherit from) standard SqlalchemyMixin in vdm
class DomainObject(object):
    
    text_search_fields = []

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def by_name(self, name, autoflush=True):
        obj = Session.query(self).autoflush(autoflush).filter_by(name=name).first()
        return obj

    @classmethod
    def text_search(self, query, term):
        register = self
        make_like = lambda x,y: x.ilike('%' + y + '%')
        q = None
        for field in self.text_search_fields:
            attr = getattr(register, field)
            q = or_(q, make_like(attr, term))
        return query.filter(q)

    @classmethod
    def active(self):
        from core import State
        return Session.query(self).filter_by(state=State.ACTIVE)

    def purge(self):
        sess = orm.object_session(self)
        if hasattr(self, '__revisioned__'): # only for versioned objects ...
            # this actually should auto occur due to cascade relationships but
            # ...
            for rev in self.all_revisions:
                sess.delete(rev)
        sess.delete(self)

    def as_dict(self):
        _dict = OrderedDict()
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            val = getattr(self, col.name)
            if isinstance(val, datetime.date):
                val = str(val)
            _dict[col.name] = val
        return _dict

    def __str__(self):
        return self.__unicode__().encode('utf8')

    def __unicode__(self):
        repr = u'<%s' % self.__class__.__name__
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            repr += u' %s=%s' % (col.name, getattr(self, col.name))
        repr += '>'
        return repr

    def __repr__(self):
        return self.__unicode__().encode('utf-8')
