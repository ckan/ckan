import meta
import datetime
import sqlalchemy

import core
import ckan.model
import domain_object


class ModelFollowingModel(domain_object.DomainObject):
    def __init__(self, follower_id, object_id):
        self.follower_id = follower_id
        self.object_id = object_id
        self.datetime = datetime.datetime.now()

    @classmethod
    def get(cls, follower_id, object_id):
        '''Return a ModelFollowingModel object for the given follower_id and
        object_id, or None if no such follower exists.

        '''
        query = cls._get(follower_id, object_id)
        following = cls._filter_following_objects(query)
        if len(following) == 1:
            return following[0]

    @classmethod
    def is_following(cls, follower_id, object_id):
        '''Return True if follower_id is currently following object_id, False
        otherwise.

        '''
        return cls.get(follower_id, object_id) is not None

    @classmethod
    def followee_count(cls, follower_id):
        '''Return the number of objects followed by the follower.'''
        return cls._get_followees(follower_id).count()

    @classmethod
    def followee_list(cls, follower_id):
        '''Return a list of objects followed by the follower.'''
        query = cls._get_followees(follower_id).all()
        followees = cls._filter_following_objects(query)
        return followees

    @classmethod
    def follower_count(cls, object_id):
        '''Return the number of followers of the object.'''
        return cls._get_followers(object_id).count()

    @classmethod
    def follower_list(cls, object_id):
        '''Return a list of followers of the object.'''
        query = cls._get_followers(object_id).all()
        followers = cls._filter_following_objects(query)
        return followers

    @classmethod
    def _filter_following_objects(cls, query):
        return [q[0] for q in query]

    @classmethod
    def _get_followees(cls, follower_id):
        return cls._get(follower_id)

    @classmethod
    def _get_followers(cls, object_id):
        return cls._get(None, object_id)

    @classmethod
    def _get(cls, follower_id=None, object_id=None):
        follower_alias = sqlalchemy.orm.aliased(cls._follower_class())
        object_alias = sqlalchemy.orm.aliased(cls._object_class())

        follower_id = follower_id or cls.follower_id
        object_id = object_id or cls.object_id

        query = meta.Session.query(cls, follower_alias, object_alias)\
            .filter(sqlalchemy.and_(
                follower_alias.id == follower_id,
                cls.follower_id == follower_alias.id,
                cls.object_id == object_alias.id,
                follower_alias.state != core.State.DELETED,
                object_alias.state != core.State.DELETED,
                object_alias.id == object_id))

        return query


class UserFollowingUser(ModelFollowingModel):
    '''A many-many relationship between users.

    A relationship between one user (the follower) and another (the object),
    that means that the follower is currently following the object.

    '''
    @classmethod
    def _follower_class(cls):
        return ckan.model.User

    @classmethod
    def _object_class(cls):
        return ckan.model.User


user_following_user_table = sqlalchemy.Table('user_following_user',
        meta.metadata,
    sqlalchemy.Column('follower_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True, nullable=False),
    sqlalchemy.Column('object_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True, nullable=False),
    sqlalchemy.Column('datetime', sqlalchemy.types.DateTime, nullable=False),
)

meta.mapper(UserFollowingUser, user_following_user_table)

class UserFollowingDataset(ModelFollowingModel):
    '''A many-many relationship between users and datasets (packages).

    A relationship between a user (the follower) and a dataset (the object),
    that means that the user is currently following the dataset.

    '''
    @classmethod
    def _follower_class(cls):
        return ckan.model.User

    @classmethod
    def _object_class(cls):
        return ckan.model.Package


user_following_dataset_table = sqlalchemy.Table('user_following_dataset',
        meta.metadata,
    sqlalchemy.Column('follower_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True, nullable=False),
    sqlalchemy.Column('object_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('package.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True, nullable=False),
    sqlalchemy.Column('datetime', sqlalchemy.types.DateTime, nullable=False),
)

meta.mapper(UserFollowingDataset, user_following_dataset_table)


class UserFollowingGroup(ModelFollowingModel):
    '''A many-many relationship between users and groups.

    A relationship between a user (the follower) and a group (the object),
    that means that the user is currently following the group.

    '''
    @classmethod
    def _follower_class(cls):
        return ckan.model.User

    @classmethod
    def _object_class(cls):
        return ckan.model.Group

user_following_group_table = sqlalchemy.Table('user_following_group',
        meta.metadata,
    sqlalchemy.Column('follower_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True, nullable=False),
    sqlalchemy.Column('object_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('group.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True, nullable=False),
    sqlalchemy.Column('datetime', sqlalchemy.types.DateTime, nullable=False),
)

meta.mapper(UserFollowingGroup, user_following_group_table)
