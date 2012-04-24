import sqlalchemy
import core
import meta
import datetime

# FIXME: Should follower_type and object_type be part of the primary key too?
# FIXME: Should follower rows be automatically deleted when the objects are deleted?
follower_table = sqlalchemy.Table('follower',
        meta.metadata,
    sqlalchemy.Column('follower_id', sqlalchemy.types.UnicodeText,
        nullable=False, primary_key=True),
    sqlalchemy.Column('follower_type', sqlalchemy.types.UnicodeText,
        nullable=False),
    sqlalchemy.Column('object_id', sqlalchemy.types.UnicodeText,
        nullable=False, primary_key=True),
    sqlalchemy.Column('object_type', sqlalchemy.types.UnicodeText,
        nullable=False),
    sqlalchemy.Column('datetime', sqlalchemy.types.DateTime, nullable=False),
)

class Follower(core.DomainObject):
    '''A follower relationship between one domain object and another.

    A Follower is a relationship between one domain object, the follower (e.g.
    a user), and another domain object, the object (e.g. another user or a
    dataset). The follower relationship declares that one object is currently
    following another. For example, a user may follow another user or a
    dataset.

    '''
    def __init__(self, follower_id, follower_type, object_id, object_type):
        self.follower_id = follower_id
        self.follower_type = follower_type
        self.object_id = object_id
        self.object_type = object_type
        self.datetime = datetime.datetime.now()

    @classmethod
    def get(self, follower_id, object_id):
        '''Return a Follower object for the given follower_id and object_id,
        or None if no such follower exists.

        '''
        query = meta.Session.query(Follower)
        query = query.filter(Follower.follower_id==follower_id)
        query = query.filter(Follower.object_id==object_id)
        return query.first()

    @classmethod
    def follower_count(cls, object_id):
        '''Return the number of followers of an object.'''
        return meta.Session.query(Follower).filter(
                Follower.object_id == object_id).count()

    @classmethod
    def follower_list(cls, object_id):
        '''Return a list of all of the followers of an object.'''
        return meta.Session.query(Follower).filter(
                Follower.object_id == object_id).all()

    @classmethod
    def is_following(cls, follower_id, object_id):
        '''Return True if follower_id is currently following object_id, False
        otherwise.

        '''
        return Follower.get(follower_id, object_id) is not None

core.mapper(Follower, follower_table)
