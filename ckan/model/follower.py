import sqlalchemy
import meta
import datetime
import domain_object

class UserFollowingUser(domain_object.DomainObject):
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
    def is_following(cls, follower_id, object_id):
        '''Return True if follower_id is currently following object_id, False
        otherwise.

        '''
        return UserFollowingUser.get(follower_id, object_id) is not None


    @classmethod
    def followee_count(cls, follower_id):
        '''Return the number of users followed by a user.'''
        return meta.Session.query(UserFollowingUser).filter(
                UserFollowingUser.follower_id == follower_id).count()

    @classmethod
    def followee_list(cls, follower_id):
        '''Return a list of users followed by a user.'''
        return meta.Session.query(UserFollowingUser).filter(
                UserFollowingUser.follower_id == follower_id).all()


    @classmethod
    def follower_count(cls, user_id):
        '''Return the number of followers of a user.'''
        return meta.Session.query(UserFollowingUser).filter(
                UserFollowingUser.object_id == user_id).count()

    @classmethod
    def follower_list(cls, user_id):
        '''Return a list of followers of a user.'''
        return meta.Session.query(UserFollowingUser).filter(
                UserFollowingUser.object_id == user_id).all()


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

class UserFollowingDataset(domain_object.DomainObject):
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
    def is_following(cls, follower_id, object_id):
        '''Return True if follower_id is currently following object_id, False
        otherwise.

        '''
        return UserFollowingDataset.get(follower_id, object_id) is not None


    @classmethod
    def followee_count(cls, follower_id):
        '''Return the number of datasets followed by a user.'''
        return meta.Session.query(UserFollowingDataset).filter(
                UserFollowingDataset.follower_id == follower_id).count()

    @classmethod
    def followee_list(cls, follower_id):
        '''Return a list of datasets followed by a user.'''
        return meta.Session.query(UserFollowingDataset).filter(
                UserFollowingDataset.follower_id == follower_id).all()


    @classmethod
    def follower_count(cls, dataset_id):
        '''Return the number of followers of a dataset.'''
        return meta.Session.query(UserFollowingDataset).filter(
                UserFollowingDataset.object_id == dataset_id).count()

    @classmethod
    def follower_list(cls, dataset_id):
        '''Return a list of followers of a dataset.'''
        return meta.Session.query(UserFollowingDataset).filter(
                UserFollowingDataset.object_id == dataset_id).all()


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


class UserFollowingGroup(domain_object.DomainObject):
    '''A many-many relationship between users and groups.

    A relationship between a user (the follower) and a group (the object),
    that means that the user is currently following the group.

    '''
    def __init__(self, follower_id, object_id):
        self.follower_id = follower_id
        self.object_id = object_id
        self.datetime = datetime.datetime.now()

    @classmethod
    def get(self, follower_id, object_id):
        '''Return a UserFollowingGroup object for the given follower_id and
        object_id, or None if no such relationship exists.

        '''
        query = meta.Session.query(UserFollowingGroup)
        query = query.filter(UserFollowingGroup.follower_id == follower_id)
        query = query.filter(UserFollowingGroup.object_id == object_id)
        return query.first()

    @classmethod
    def is_following(cls, follower_id, object_id):
        '''Return True if follower_id is currently following object_id, False
        otherwise.

        '''
        return UserFollowingGroup.get(follower_id, object_id) is not None

    @classmethod
    def followee_count(cls, follower_id):
        '''Return the number of groups followed by a user.'''
        return meta.Session.query(UserFollowingGroup).filter(
                UserFollowingGroup.follower_id == follower_id).count()

    @classmethod
    def followee_list(cls, follower_id):
        '''Return a list of groups followed by a user.'''
        return meta.Session.query(UserFollowingGroup).filter(
                UserFollowingGroup.follower_id == follower_id).all()

    @classmethod
    def follower_count(cls, object_id):
        '''Return the number of users following a group.'''
        return meta.Session.query(UserFollowingGroup).filter(
                UserFollowingGroup.object_id == object_id).count()

    @classmethod
    def follower_list(cls, object_id):
        '''Return a list of the users following a group.'''
        return meta.Session.query(UserFollowingGroup).filter(
                UserFollowingGroup.object_id == object_id).all()

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
