from sqlalchemy import types

def make_uuid():
    return unicode(uuid.uuid4())

import uuid
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
    def default(self):
        # return uuid.uuid4()
        return unicode(uuid.uuid4())


import simplejson
class JsonType(types.TypeDecorator):
    '''Store data as JSON serializing on save and unserializing on use.
    '''
    impl = types.UnicodeText

    def process_bind_param(self, value, engine):
        if value is None or value == {}: # ensure we stores nulls in db not json "null"
            return None
        else:
            # ensure_ascii=False => allow unicode but still need to convert
            return unicode(simplejson.dumps(value, ensure_ascii=False))

    def process_result_value(self, value, engine):
        if value is None:
            return None
        else:
            return simplejson.loads(value)

    def copy(self):
        return JsonType(self.impl.length)

