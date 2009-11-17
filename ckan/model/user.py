from datetime import datetime

from meta import *
from core import DomainObject
from types import make_uuid

user_table = Table('user', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText),
        Column('apikey', UnicodeText, default=make_uuid),
        Column('created', DateTime, default=datetime.now),
        Column('about', UnicodeText),
        )

class User(DomainObject):
    pass

mapper(User, user_table,
    order_by=user_table.c.name)

