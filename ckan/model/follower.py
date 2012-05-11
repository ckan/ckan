import sqlalchemy
import core
import meta
import datetime

class UserFollowingUser(core.DomainObject):
    '''A many-many relationship between users.

    A relationship between one user (the follower) and another (the object),
    that means that the follower is currently following the object.

    '''
    def __init__(self, follower_id, object_id):
        self.follower_id = follower_id
        self.object_id = object_id
        self.datetime = datetime.datetime.now()

    @classmethod
    def get(self, follower_id, object_id):
        '''Return a UserFollowingUser object for the given follower_id and
        object_id, or None if no such follower exists.

        '''
        query = meta.Session.query(UserFollowingUser)
        query = query.filter(UserFollowingUser.follower_id==follower_id)
        query = query.filter(UserFollowingUser.object_id==object_id)
        return query.first()

    @classmethod
    def follower_count(cls, object_id):
        '''Return the number of users following a user.'''
        return meta.Session.query(UserFollowingUser).filter(
                UserFollowingUser.object_id == object_id).count()

    @classmethod
    def follower_list(cls, object_id):
        '''Return a list of all of the followers of a user.'''
        return meta.Session.query(UserFollowingUser).filter(
                UserFollowingUser.object_id == object_id).all()

    @classmethod
    def is_following(cls, follower_id, object_id):
        '''Return True if follower_id is currently following object_id, False
        otherwise.

        '''
        return UserFollowingUser.get(follower_id, object_id) is not None

user_following_user_table = sqlalchemy.Table('user_following_user',
        meta.metadata,
    sqlalchemy.Column('follower_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True),
    sqlalchemy.Column('object_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True),
    sqlalchemy.Column('datetime', sqlalchemy.types.DateTime, nullable=False),
)

core.mapper(UserFollowingUser, user_following_user_table)

class UserFollowingDataset(core.DomainObject):
    '''A many-many relationship between users and datasets (packages).

    A relationship between a user (the follower) and a dataset (the object),
    that means that the user is currently following the dataset.

    '''
    def __init__(self, follower_id, object_id):
        self.follower_id = follower_id
        self.object_id = object_id
        self.datetime = datetime.datetime.now()

    @classmethod
    def get(self, follower_id, object_id):
        '''Return a UserFollowingDataset object for the given follower_id and
        object_id, or None if no such follower exists.

        '''
        query = meta.Session.query(UserFollowingDataset)
        query = query.filter(UserFollowingDataset.follower_id==follower_id)
        query = query.filter(UserFollowingDataset.object_id==object_id)
        return query.first()

    @classmethod
    def follower_count(cls, object_id):
        '''Return the number of users following a dataset.'''
        return meta.Session.query(UserFollowingDataset).filter(
                UserFollowingDataset.object_id == object_id).count()

    @classmethod
    def follower_list(cls, object_id):
        '''Return a list of all of the followers of a dataset.'''
        return meta.Session.query(UserFollowingDataset).filter(
                UserFollowingDataset.object_id == object_id).all()

    @classmethod
    def is_following(cls, follower_id, object_id):
        '''Return True if follower_id is currently following object_id, False
        otherwise.

        '''
        return UserFollowingDataset.get(follower_id, object_id) is not None

user_following_dataset_table = sqlalchemy.Table('user_following_dataset',
        meta.metadata,
    sqlalchemy.Column('follower_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True),
    sqlalchemy.Column('object_id', sqlalchemy.types.UnicodeText,
        sqlalchemy.ForeignKey('package.id', onupdate='CASCADE',
            ondelete='CASCADE'),
        primary_key=True),
    sqlalchemy.Column('datetime', sqlalchemy.types.DateTime, nullable=False),
)

core.mapper(UserFollowingDataset, user_following_dataset_table)
