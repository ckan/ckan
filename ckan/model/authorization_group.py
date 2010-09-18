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

def user_in_authorization_group(user, authorization_group):
    pass
        
def add_user_to_authorization_group(user, authorization_group, role):
    pass

def remove_user_from_authorization_group(user, authorization_group):
    pass


mapper(AuthorizationGroup, authorization_group_table, properties={
       'users': relation(User, lazy=True, secondary=authorization_group_user_table, 
                         backref=backref('authorization_groups', lazy=True)) 
       },
       order_by=authorization_group_table.c.name)
    
