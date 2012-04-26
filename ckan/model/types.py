## IMPORTS FIXED
import datetime
import copy
import uuid
import simplejson as json

from sqlalchemy import types

import meta

__all__ = ['iso_date_to_datetime_for_sqlite', 'make_uuid', 'UuidType',
           'JsonType', 'JsonDictType']

def make_uuid():
    return unicode(uuid.uuid4())

class UuidType(types.TypeDecorator):
    impl = types.Unicode

    def process_bind_param(self, value, engine):
        return unicode(value)

    def process_result_value(self, value, engine):
        # return uuid.UUID(value)
        return value

    def copy(self):
        return UuidType(self.impl.length)

    @classmethod
    def default(cls):
        # return uuid.uuid4()
        return unicode(uuid.uuid4())


class JsonType(types.TypeDecorator):
    '''Store data as JSON serializing on save and unserializing on use.

    Note that default values don\'t appear to work correctly with this
    type, a workaround is to instead override ``__init__()`` to explicitly
    set any default values you expect.
    '''
    impl = types.UnicodeText

    def process_bind_param(self, value, engine):
        if value is None or value == {}: # ensure we stores nulls in db not json "null"
            return None
        else:
            # ensure_ascii=False => allow unicode but still need to convert
            return unicode(json.dumps(value, ensure_ascii=False))

    def process_result_value(self, value, engine):
        if value is None:
            return {}
        else:
            return json.loads(value)

    def copy(self):
        return JsonType(self.impl.length)

    def is_mutable(self):
        return True

    def copy_value(self, value):
        return copy.copy(value)

class JsonDictType(JsonType):

    impl = types.UnicodeText

    def process_bind_param(self, value, engine):
        if value is None or value == {}: # ensure we stores nulls in db not json "null"
            return None
        else:
            if isinstance(value, basestring):
                return unicode(value)
            else:
                return unicode(json.dumps(value, ensure_ascii=False))

    def copy(self):
        return JsonDictType(self.impl.length)

def iso_date_to_datetime_for_sqlite(datetime_or_iso_date_if_sqlite):
    # Because sqlite cannot store dates properly (see this:
    # http://www.sqlalchemy.org/docs/dialects/sqlite.html#date-and-time-types )
    # when you get a result from a date field in the database, you need
    # to call this to convert it into a datetime type. When running on
    # postgres then you have a datetime anyway, so this function doesn't
    # do anything.
    if meta.engine_is_sqlite() and isinstance(datetime_or_iso_date_if_sqlite, basestring):
        return datetime.datetime.strptime(datetime_or_iso_date_if_sqlite,
                                          '%Y-%m-%d %H:%M:%S.%f')
    else:
        return datetime_or_iso_date_if_sqlite
