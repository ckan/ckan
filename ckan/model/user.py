from datetime import datetime

from meta import *
from core import DomainObject
from types import make_uuid

user_table = Table('user', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText),
        Column('openid', UnicodeText),
        Column('password', UnicodeText),
        Column('display_name', UnicodeText),
        Column('apikey', UnicodeText, default=make_uuid),
        Column('created', DateTime, default=datetime.now),
        Column('about', UnicodeText),
        )

class User(DomainObject):
    
    @classmethod
    def by_openid(self, openid):
        obj = Session.query(self).autoflush(False)
        return obj.filter_by(openid=openid).first()

mapper(User, user_table,
    order_by=user_table.c.name)

