import datetime

from meta import *
from core import DomainObject
from user import User, user_table
from types import make_uuid

authorization_group_table = Table('authorization_group', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('name', UnicodeText),
    Column('created', DateTime, default=datetime.datetime.now),
    )

authorization_group_user_table = Table('authorization_group_user', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('authorization_group_id', UnicodeText, ForeignKey('authorization_group.id'), 
           nullable=False),
    Column('user_id', UnicodeText, ForeignKey('user.id'), nullable=False)
    )


class AuthorizationGroup(DomainObject):

    @classmethod
    def search(cls, querystr, sqlalchemy_query=None):
        '''Search name.         
        '''
        import ckan.model as model
        if sqlalchemy_query is None:
            query = model.Session.query(cls)
        else:
            query = sqlalchemy_query
        qstr = '%' + querystr + '%'
        query = query.filter(or_(
            cls.name.ilike(qstr)))
        return query

    @classmethod
    def get(cls, auth_group_reference):
        query = Session.query(cls).autoflush(False)
        query = query.filter(or_(cls.name==auth_group_reference,
                                 cls.id==auth_group_reference))
        return query.first()
    
class AuthorizationGroupUser(DomainObject):
    pass

def user_in_authorization_group(user, authorization_group):
    q = Session.query(AuthorizationGroup)
    q = q.filter_by(id=authorization_group.id)
    q = q.filter(AuthorizationGroup.users.contains(user))
    return q.count() == 1
        
def add_user_to_authorization_group(user, authorization_group, role):
    assert not user_in_authorization_group(user, authorization_group)
    from authz import add_user_to_role
    Session.add(authorization_group)
    authorization_group.users.append(user)
    add_user_to_role(user, role, authorization_group)

def remove_user_from_authorization_group(user, authorization_group):
    assert user_in_authorization_group(user, authorization_group)
    from authz import remove_user_from_role, AuthorizationGroupRole
    Session.add(authorization_group)
    authorization_group.users.remove(user)
    q = Session.query(AuthorizationGroupRole)
    q = q.filter_by(authorization_group=authorization_group,
                    user=user)
    for agr in q:
        remove_user_from_role(user, agr.role, authorization_group)
    


mapper(AuthorizationGroup, authorization_group_table, properties={
       'users': relation(User, lazy=True, secondary=authorization_group_user_table, 
                         backref=backref('authorization_groups', lazy=True)) 
       },
       order_by=authorization_group_table.c.name)
    
mapper(AuthorizationGroupUser, authorization_group_user_table)
