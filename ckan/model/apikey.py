# TODO: have moved content into __init__.py but should move back at some point
import uuid

def make_uuid():
    return str(uuid.uuid4())

apikey_table = Table('license', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('name', types.UnicodeText),
        Column('key', types.Unicode(36), default=make_uuid)
        )

class ApiKey(DomainObject):
    pass

mapper(ApiKey, apikey_table,
    order_by=apikey_table.c.id)
