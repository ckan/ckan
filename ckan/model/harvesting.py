import datetime
from meta import *

from types import make_uuid
from core import *
from domain_object import DomainObject

__all__ = ['HarvestSource', 'harvest_source_table']

class DomainObject(DomainObject):

    key_attr = 'id'

    def delete(self):
        self.purge()

    @classmethod 
    def get(self, key, default=Exception, attr=None):
        """Finds a single entity in the register."""
        if attr == None:
            attr = self.key_attr
        kwds = {attr: key}
        q = Session.query(self).autoflush(False)
        o = q.filter_by(**kwds).first()
        if o:
            return o
        if default != Exception:
            return default
        else:
            raise Exception, "%s not found: %s" % (self.__name__, key)


class HarvestSource(DomainObject): pass
    

harvest_source_table = Table('harvest_source', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('url', types.UnicodeText, unique=True, nullable=False),
        Column('description', types.UnicodeText),                      
        Column('userRef', types.UnicodeText),
        Column('publisherRef', types.UnicodeText),
        Column('status', types.UnicodeText),
        Column('created', DateTime, default=datetime.datetime.utcnow),
)

mapper(HarvestSource, harvest_source_table, properties={ })

