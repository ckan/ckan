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

from ckan.common import config
import ckan.model
from ckan.model import meta
from ckan.model import domain_object, types as _types

__all__ = ['Activity', 'activity_table',
           'ActivityDetail', 'activity_detail_table',
           ]

activity_table = Table(
    'activity', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('timestamp', types.DateTime),
    Column('user_id', types.UnicodeText),
    Column('object_id', types.UnicodeText),
    # legacy revision_id values are used by migrate_package_activity.py
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

    def __init__(
            self, user_id, object_id, activity_type, data=None):
        self.id = _types.make_uuid()
        self.timestamp = datetime.datetime.utcnow()
        self.user_id = user_id
        self.object_id = object_id
        self.activity_type = activity_type
        if data is None:
            self.data = {}
        else:
            self.data = data

    @classmethod
    def get(cls, id):
        '''Returns an Activity object referenced by its id.'''
        if not id:
            return None

        return meta.Session.query(cls).get(id)


meta.mapper(Activity, activity_table)


# deprecated
class ActivityDetail(domain_object.DomainObject):

    def __init__(
            self, activity_id, object_id, object_type, activity_type,
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
            .filter_by(activity_id=activity_id).all()


meta.mapper(ActivityDetail, activity_detail_table, properties={
    'activity': orm.relation(Activity, backref=orm.backref('activity_detail'))
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
    Return union of two or more activity queries sorted by timestamp,
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

    q = _filter_activitites_from_users(q)

    return _activities_at_offset(q, limit, offset)


def _package_activity_query(package_id):
    '''Return an SQLAlchemy query for all activities about package_id.

    '''
    import ckan.model as model
    q = model.Session.query(model.Activity) \
        .filter_by(object_id=package_id)
    return q


def package_activity_list(
        package_id, limit, offset, include_hidden_activity=False):
    '''Return the given dataset (package)'s public activity stream.

    Returns all activities about the given dataset, i.e. where the given
    dataset is the object of the activity, e.g.:

    "{USER} created the dataset {DATASET}"
    "{USER} updated the dataset {DATASET}"
    etc.

    '''
    q = _package_activity_query(package_id)

    if not include_hidden_activity:
        q = _filter_activitites_from_users(q)

    return _activities_at_offset(q, limit, offset)


def _group_activity_query(group_id, include_hidden_activity=False):
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
        )
    ).outerjoin(
        model.Package,
        and_(
            or_(model.Package.id == model.Member.table_id,
                model.Package.owner_org == group_id),
            model.Package.private == False,
        )
    ).filter(
        # We only care about activity either on the group itself or on packages
        # within that group.
        # FIXME: This means that activity that occured while a package belonged
        # to a group but was then removed will not show up. This may not be
        # desired but is consistent with legacy behaviour.
        or_(
            # active dataset in the group
            and_(model.Member.group_id == group_id,
                 model.Member.state == 'active',
                 model.Package.state == 'active'),
            # deleted dataset in the group
            and_(model.Member.group_id == group_id,
                 model.Member.state == 'deleted',
                 model.Package.state == 'deleted'),
                 # (we want to avoid showing changes to an active dataset that
                 # was once in this group)
            # activity the the group itself
            model.Activity.object_id == group_id,
        )
    )

    if not include_hidden_activity:
        q = _filter_activitites_from_users(q)

    return q


def _organization_activity_query(org_id, include_hidden_activity=False):
    '''Return an SQLAlchemy query for all activities about org_id.

    Returns a query for all activities whose object is either the org itself
    or one of the org's datasets.

    '''
    import ckan.model as model

    org = model.Group.get(org_id)
    if not org or not org.is_organization:
        # Return a query with no results.
        return model.Session.query(model.Activity).filter(text('0=1'))

    q = model.Session.query(
        model.Activity
    ).outerjoin(
        model.Package,
        and_(
            model.Package.id == model.Activity.object_id,
            model.Package.private == False,
        )
    ).filter(
        # We only care about activity either on the the org itself or on
        # packages within that org.
        # FIXME: This means that activity that occured while a package belonged
        # to a org but was then removed will not show up. This may not be
        # desired but is consistent with legacy behaviour.
        or_(
            model.Package.owner_org == org_id,
            model.Activity.object_id == org_id
        )
    )
    if not include_hidden_activity:
        q = _filter_activitites_from_users(q)

    return q


def group_activity_list(group_id, limit, offset, include_hidden_activity=False):

    '''Return the given group's public activity stream.

    Returns activities where the given group or one of its datasets is the
    object of the activity, e.g.:

    "{USER} updated the group {GROUP}"
    "{USER} updated the dataset {DATASET}"
    etc.

    '''
    q = _group_activity_query(group_id, include_hidden_activity)
    return _activities_at_offset(q, limit, offset)


def organization_activity_list(
        group_id, limit, offset, include_hidden_activity=False):
    '''Return the given org's public activity stream.

    Returns activities where the given org or one of its datasets is the
    object of the activity, e.g.:

    "{USER} updated the organization {ORG}"
    "{USER} updated the dataset {DATASET}"
    etc.

    '''
    q = _organization_activity_query(group_id, include_hidden_activity)
    return _activities_at_offset(q, limit, offset)


def _activities_from_users_followed_by_user_query(user_id, limit):
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
    q1 = _activities_from_users_followed_by_user_query(user_id, limit)
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

    q = _filter_activitites_from_users(q)

    return _activities_at_offset(q, limit, offset)


def _changed_packages_activity_query():
    '''Return an SQLAlchemy query for all changed package activities.

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

    q = _filter_activitites_from_users(q)

    return _activities_at_offset(q, limit, offset)


def _filter_activitites_from_users(q):
    '''
    Adds a filter to an existing query object ot avoid activities from users
    defined in :ref:`ckan.hide_activity_from_users` (defaults to the site user)
    '''
    users_to_avoid = _activity_stream_get_filtered_users()
    if users_to_avoid:
        q = q.filter(ckan.model.Activity.user_id.notin_(users_to_avoid))

    return q


def _activity_stream_get_filtered_users():
    '''
    Get the list of users from the :ref:`ckan.hide_activity_from_users` config
    option and return a list of their ids. If the config is not specified,
    returns the id of the site user.
    '''
    users = config.get('ckan.hide_activity_from_users')
    if users:
        users_list = users.split()
    else:
        from ckan.logic import get_action
        context = {'ignore_auth': True}
        site_user = get_action('get_site_user')(context)
        users_list = [site_user.get('name')]

    return ckan.model.User.user_ids_for_name_or_id(users_list)
