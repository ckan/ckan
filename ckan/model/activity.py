# encoding: utf-8

import datetime

from sqlalchemy import (
    orm,
    types,
    Column,
    Table,
    ForeignKey,
    desc,
    or_,
    and_,
    union_all,
    text,
)

import ckan.model
import meta
import types as _types
import domain_object

__all__ = ['Activity', 'activity_table',
           'ActivityDetail', 'activity_detail_table',
           ]

activity_table = Table(
    'activity', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('timestamp', types.DateTime),
    Column('user_id', types.UnicodeText),
    Column('object_id', types.UnicodeText),
    Column('revision_id', types.UnicodeText),
    Column('activity_type', types.UnicodeText),
    Column('data', _types.JsonDictType),
    )

activity_detail_table = Table(
    'activity_detail', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('activity_id', types.UnicodeText, ForeignKey('activity.id')),
    Column('object_id', types.UnicodeText),
    Column('object_type', types.UnicodeText),
    Column('activity_type', types.UnicodeText),
    Column('data', _types.JsonDictType),
    )

class Activity(domain_object.DomainObject):

    def __init__(self, user_id, object_id, revision_id, activity_type,
            data=None):
        self.id = _types.make_uuid()
        self.timestamp = datetime.datetime.utcnow()
        self.user_id = user_id
        self.object_id = object_id
        self.revision_id = revision_id
        self.activity_type = activity_type
        if data is None:
            self.data = {}
        else:
            self.data = data

meta.mapper(Activity, activity_table)


class ActivityDetail(domain_object.DomainObject):

    def __init__(self, activity_id, object_id, object_type, activity_type,
            data=None):
        self.activity_id = activity_id
        self.object_id = object_id
        self.object_type = object_type
        self.activity_type = activity_type
        if data is None:
            self.data = {}
        else:
            self.data = data

    @classmethod
    def by_activity_id(cls, activity_id):
        return ckan.model.Session.query(cls) \
                .filter_by(activity_id = activity_id).all()


meta.mapper(ActivityDetail, activity_detail_table, properties = {
    'activity':orm.relation ( Activity, backref=orm.backref('activity_detail'))
    })


def _activities_limit(q, limit, offset=None):
    '''
    Return an SQLAlchemy query for all activities at an offset with a limit.
    '''
    import ckan.model as model
    q = q.order_by(desc(model.Activity.timestamp))
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q

def _activities_union_all(*qlist):
    '''
    Return union of two or more queries sorted by timestamp,
    and remove duplicates
    '''
    import ckan.model as model
    return model.Session.query(model.Activity).select_entity_from(
        union_all(*[q.subquery().select() for q in qlist])
        ).distinct(model.Activity.timestamp)

def _activities_at_offset(q, limit, offset):
    '''
    Return a list of all activities at an offset with a limit.
    '''
    return _activities_limit(q, limit, offset).all()

def _activities_from_user_query(user_id):
    '''Return an SQLAlchemy query for all activities from user_id.'''
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.filter(model.Activity.user_id == user_id)
    return q


def _activities_about_user_query(user_id):
    '''Return an SQLAlchemy query for all activities about user_id.'''
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.filter(model.Activity.object_id == user_id)
    return q


def _user_activity_query(user_id, limit):
    '''Return an SQLAlchemy query for all activities from or about user_id.'''
    q1 = _activities_limit(_activities_from_user_query(user_id), limit)
    q2 = _activities_limit(_activities_about_user_query(user_id), limit)
    return _activities_union_all(q1, q2)


def user_activity_list(user_id, limit, offset):
    '''Return user_id's public activity stream.

    Return a list of all activities from or about the given user, i.e. where
    the given user is the subject or object of the activity, e.g.:

    "{USER} created the dataset {DATASET}"
    "{OTHER_USER} started following {USER}"
    etc.

    '''
    q = _user_activity_query(user_id, limit + offset)
    return _activities_at_offset(q, limit, offset)


def _package_activity_query(package_id):
    '''Return an SQLAlchemy query for all activities about package_id.

    '''
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.filter_by(object_id=package_id)
    return q


def package_activity_list(package_id, limit, offset):
    '''Return the given dataset (package)'s public activity stream.

    Returns all activities  about the given dataset, i.e. where the given
    dataset is the object of the activity, e.g.:

    "{USER} created the dataset {DATASET}"
    "{USER} updated the dataset {DATASET}"
    etc.

    '''
    q = _package_activity_query(package_id)
    return _activities_at_offset(q, limit, offset)


def _group_activity_query(group_id):
    '''Return an SQLAlchemy query for all activities about group_id.

    Returns a query for all activities whose object is either the group itself
    or one of the group's datasets.

    '''
    import ckan.model as model

    group = model.Group.get(group_id)
    if not group:
        # Return a query with no results.
        return model.Session.query(model.Activity).filter(text('0=1'))

    q = model.Session.query(
        model.Activity
    ).outerjoin(
        model.Member,
        and_(
            model.Activity.object_id == model.Member.table_id,
            model.Member.state == 'active'
        )
    ).outerjoin(
        model.Package,
        and_(
            model.Package.id == model.Member.table_id,
            model.Package.private == False,
            model.Package.state == 'active'
        )
    ).filter(
        # We only care about activity either on the the group itself or on
        # packages within that group.
        # FIXME: This means that activity that occured while a package belonged
        # to a group but was then removed will not show up. This may not be
        # desired but is consistent with legacy behaviour.
        or_(
            model.Member.group_id == group_id,
            model.Activity.object_id == group_id
        ),
    )

    return q


def group_activity_list(group_id, limit, offset):
    '''Return the given group's public activity stream.

    Returns all activities where the given group or one of its datasets is the
    object of the activity, e.g.:

    "{USER} updated the group {GROUP}"
    "{USER} updated the dataset {DATASET}"
    etc.

    '''
    q = _group_activity_query(group_id)
    return _activities_at_offset(q, limit, offset)


def _activites_from_users_followed_by_user_query(user_id, limit):
    '''Return a query for all activities from users that user_id follows.'''
    import ckan.model as model

    # Get a list of the users that the given user is following.
    follower_objects = model.UserFollowingUser.followee_list(user_id)
    if not follower_objects:
        # Return a query with no results.
        return model.Session.query(model.Activity).filter(text('0=1'))

    return _activities_union_all(*[
        _user_activity_query(follower.object_id, limit)
        for follower in follower_objects])


def _activities_from_datasets_followed_by_user_query(user_id, limit):
    '''Return a query for all activities from datasets that user_id follows.'''
    import ckan.model as model

    # Get a list of the datasets that the user is following.
    follower_objects = model.UserFollowingDataset.followee_list(user_id)
    if not follower_objects:
        # Return a query with no results.
        return model.Session.query(model.Activity).filter(text('0=1'))

    return _activities_union_all(*[
        _activities_limit(_package_activity_query(follower.object_id), limit)
        for follower in follower_objects])


def _activities_from_groups_followed_by_user_query(user_id, limit):
    '''Return a query for all activities about groups the given user follows.

    Return a query for all activities about the groups the given user follows,
    or about any of the group's datasets. This is the union of
    _group_activity_query(group_id) for each of the groups the user follows.

    '''
    import ckan.model as model

    # Get a list of the group's that the user is following.
    follower_objects = model.UserFollowingGroup.followee_list(user_id)
    if not follower_objects:
        # Return a query with no results.
        return model.Session.query(model.Activity).filter(text('0=1'))

    return _activities_union_all(*[
        _activities_limit(_group_activity_query(follower.object_id), limit)
        for follower in follower_objects])


def _activities_from_everything_followed_by_user_query(user_id, limit):
    '''Return a query for all activities from everything user_id follows.'''
    q1 = _activites_from_users_followed_by_user_query(user_id, limit)
    q2 = _activities_from_datasets_followed_by_user_query(user_id, limit)
    q3 = _activities_from_groups_followed_by_user_query(user_id, limit)
    return _activities_union_all(q1, q2, q3)


def activities_from_everything_followed_by_user(user_id, limit, offset):
    '''Return activities from everything that the given user is following.

    Returns all activities where the object of the activity is anything
    (user, dataset, group...) that the given user is following.

    '''
    q = _activities_from_everything_followed_by_user_query(
        user_id,
        limit + offset)
    return _activities_at_offset(q, limit, offset)


def _dashboard_activity_query(user_id, limit):
    '''Return an SQLAlchemy query for user_id's dashboard activity stream.'''
    q1 = _user_activity_query(user_id, limit)
    q2 = _activities_from_everything_followed_by_user_query(user_id, limit)
    return _activities_union_all(q1, q2)


def dashboard_activity_list(user_id, limit, offset):
    '''Return the given user's dashboard activity stream.

    Returns activities from the user's public activity stream, plus
    activities from everything that the user is following.

    This is the union of user_activity_list(user_id) and
    activities_from_everything_followed_by_user(user_id).

    '''
    q = _dashboard_activity_query(user_id, limit + offset)
    return _activities_at_offset(q, limit, offset)

def _changed_packages_activity_query():
    '''Return an SQLAlchemyu query for all changed package activities.

    Return a query for all activities with activity_type '*package', e.g.
    'new_package', 'changed_package', 'deleted_package'.

    '''
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.filter(model.Activity.activity_type.endswith('package'))
    return q


def recently_changed_packages_activity_list(limit, offset):
    '''Return the site-wide stream of recently changed package activities.

    This activity stream includes recent 'new package', 'changed package' and
    'deleted package' activities for the whole site.

    '''
    q = _changed_packages_activity_query()
    return _activities_at_offset(q, limit, offset)
