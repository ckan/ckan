from meta import *
from core import DomainObject
import types

# API Key
# import apikey # TODO: see apikey.py
apikey_table = Table('apikey', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', UnicodeText),
        Column('key', types.UuidType, default=types.UuidType.default)
        )

class ApiKey(DomainObject):
    pass

mapper(ApiKey, apikey_table,
    order_by=apikey_table.c.id)

