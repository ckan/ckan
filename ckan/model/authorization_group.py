from datetime import datetime

from meta import *
from core import DomainObject
from user import User, user_table
from types import make_uuid

authorization_group_table = Table('authorization_group', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('name', UnicodeText),
    Column('created', DateTime, default=datetime.now),
    )

authorization_group_user_table = Table('authorization_group_user', metadata,
    Column('authorization_group_id', UnicodeText, ForeignKey('authorization_group.id'), nullable=False),
    Column('user_id', UnicodeText, ForeignKey('user.id'), nullable=False)
    )


class AuthorizationGroup(DomainObject):
    pass


mapper(AuthorizationGroup, authorization_group_table, properties={
       'users': relation(User, lazy=True, secondary=authorization_group_user_table, 
                         backref=backref('authorization_groups', lazy=True)) 
       },
       order_by=authorization_group_table.c.name)
    
