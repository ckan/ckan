import datetime

from sqlalchemy import orm, types, Column, Table, ForeignKey, or_

import meta
import user
import types as _types
import domain_object

__all__ = ['AuthorizationGroup', 'AuthorizationGroupUser',
           'user_in_authorization_group', 'add_user_to_authorization_group',
           'remove_user_from_authorization_group']

authorization_group_table = Table('authorization_group', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('name', types.UnicodeText),
    Column('created', types.DateTime, default=datetime.datetime.now),
    )

authorization_group_user_table = Table('authorization_group_user', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('authorization_group_id', types.UnicodeText, ForeignKey('authorization_group.id'),
           nullable=False),
    Column('user_id', types.UnicodeText, ForeignKey('user.id'), nullable=False)
    )


class AuthorizationGroup(domain_object.DomainObject):

    @classmethod
    def search(cls, querystr, sqlalchemy_query=None):
        '''Search name.
        '''
        if sqlalchemy_query is None:
            query = meta.Session.query(cls)
        else:
            query = sqlalchemy_query
        qstr = '%' + querystr + '%'
        query = query.filter(or_(
            cls.name.ilike(qstr)))
        return query

    @classmethod
    def get(cls, auth_group_reference):
        query = meta.Session.query(cls).autoflush(False)
        query = query.filter(or_(cls.name==auth_group_reference,
                                 cls.id==auth_group_reference))
        return query.first()

class AuthorizationGroupUser(domain_object.DomainObject):
    pass

def user_in_authorization_group(user, authorization_group):
    q = meta.Session.query(AuthorizationGroup)
    q = q.filter_by(id=authorization_group.id)
    q = q.filter(AuthorizationGroup.users.contains(user))
    return q.count() == 1

def add_user_to_authorization_group(user, authorization_group, role):
    assert not user_in_authorization_group(user, authorization_group)
    from authz import add_user_to_role
    meta.Session.add(authorization_group)
    authorization_group.users.append(user)
    add_user_to_role(user, role, authorization_group)

def remove_user_from_authorization_group(user, authorization_group):
    assert user_in_authorization_group(user, authorization_group)
    from authz import remove_user_from_role, AuthorizationGroupRole
    meta.Session.add(authorization_group)
    authorization_group.users.remove(user)
    q = meta.Session.query(AuthorizationGroupRole)
    q = q.filter_by(authorization_group=authorization_group,
                    user=user)
    for agr in q:
        remove_user_from_role(user, agr.role, authorization_group)



meta.mapper(AuthorizationGroup, authorization_group_table, properties={
       'users': orm.relation(user.User, lazy=True, secondary=authorization_group_user_table,
                         backref=orm.backref('authorization_groups', lazy=True))
       },
       order_by=authorization_group_table.c.name)

meta.mapper(AuthorizationGroupUser, authorization_group_user_table)
