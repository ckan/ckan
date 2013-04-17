import datetime

from sqlalchemy import orm

from meta import *
from types import make_uuid
from types import JsonDictType
from core import *
from package import *

__all__ = ['DataCache', 'data_cache_table']

data_cache_table = Table(
    'data_cache', metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('object_id', types.UnicodeText),
    Column('key', types.UnicodeText),
    Column('value', types.UnicodeText),
    Column('created', DateTime, default=datetime.datetime.now),
)


class DataCache(DomainObject):
    """
    DataCache provides simple caching of pre-calculated values for queries that
    would take too long to run in real time.  It allows background tasks to determine
    what it wants to store, and then uses this model to store that data, so that
    at request time the data can be fetched in bulk.

    This model makes no assumptions on what is stored, and so it is up to the producer
    and consumer to agree on a format for the value stored.  It is suggested that for
    data that is not a basic type (int, string etc) that json is used as decoding of
    JSON will still be a lot faster than performing the initial queries.

    Example usage:

        >>> pub_id = '1234'
        >>> DataCache.set(pub_id, "broken_link_count", 2112)
        >>> DataCache.get(pub_id, "broken_link_count")
        2112
    """

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def get(cls, object_id, key):
        """
        Retrieves the value and how long ago (in seconds) that it was written if the
        record with object_id/key exists. If not it will return None/None.
        """
        if not object_id or not key:
            return None, None
        item = Session.query(cls).filter(cls.key==key).filter(cls.object_id==object_id).first()
        if not item:
            return (None, None,)
        td = datetime.datetime.now() - item.created
        total_seconds = ((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6)
        return item.value, total_seconds

    @classmethod
    def get_fresh(cls, objectid, key, hours=24):
        """
        Checks cache for the specified objectid and key and if it exists, and is
        less than 'hours' old it will be returned.  If not present, or too old then
        this function returns None.
        """
        import json
        from ckan.lib.jsonp import DateTimeJsonDecoder

        val, age = cls.get(objectid, key)
        if not val:
            return None

        if age and age > (hours * 60 * 60):
            return None

        return json.loads(val, cls=DateTimeJsonDecoder)


    @classmethod
    def set(cls, object_id, key, value):
        """
        This method looks up any existing record for the object_id/key and if found
        will update the value and created fields, otherwise it will create a new record.
        All values will be returned as a string and it is up to the caller to perform the
        relevant casting.
        """
        if not object_id or not key:
            return False

        item = Session.query(cls).filter(cls.key==key).filter(cls.object_id==object_id).first()
        if item == None:
            item = DataCache(object_id=object_id, key=key, value=value)
        else:
            item.value = value
            item.created = datetime.datetime.now()

        Session.add(item)
        Session.flush()
        return True

mapper(DataCache, data_cache_table)
