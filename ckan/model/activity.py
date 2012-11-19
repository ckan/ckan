import datetime

from sqlalchemy import orm, types, Column, Table, ForeignKey, desc

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
        self.timestamp = datetime.datetime.now()
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


meta.mapper(ActivityDetail, activity_detail_table, properties = {
    'activity':orm.relation ( Activity, backref=orm.backref('activity_detail'))
    })


def _most_recent_activities(q, limit):
    import ckan.model as model
    q = q.order_by(desc(model.Activity.timestamp))
    if limit:
        q = q.limit(limit)
    return q.all()


def _activities_from_user_query(user_id):
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.filter(model.Activity.user_id == user_id)
    return q


def _activities_about_user_query(user_id):
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.filter(model.Activity.object_id == user_id)
    return q


def _user_activity_query(user_id):
    q = _activities_from_user_query(user_id)
    q = q.union(_activities_about_user_query(user_id))
    return q


def user_activity_list(user_id, limit=15):
    '''Return the given user's public activity stream.

    Returns all activities from or about the given user, i.e. where the given
    user is the subject or object of the activity, e.g.:

    "{USER} created the dataset {DATASET}"
    "{OTHER_USER} started following {USER}"
    etc.

    '''
    q = _user_activity_query(user_id)
    return _most_recent_activities(q, limit)


def _package_activity_query(package_id):
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.filter_by(object_id=package_id)
    return q


def package_activity_list(package_id, limit=15):
    '''Return the given dataset (package)'s public activity stream.

    Returns all activities  about the given dataset, i.e. where the given
    dataset is the object of the activity, e.g.:

    "{USER} created the dataset {DATASET}"
    "{USER} updated the dataset {DATASET}"
    etc.

    '''
    q = _package_activity_query(package_id)
    return _most_recent_activities(q, limit)


def _activites_from_users_followed_by_user_query(user_id):
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.join(model.UserFollowingUser,
            model.UserFollowingUser.object_id == model.Activity.user_id)
    q = q.filter(model.UserFollowingUser.follower_id == user_id)
    return q


def _activities_from_datasets_followed_by_user_query(user_id):
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.join(model.UserFollowingDataset,
            model.UserFollowingDataset.object_id == model.Activity.object_id)
    q = q.filter(model.UserFollowingDataset.follower_id == user_id)
    return q


def _activities_from_everything_followed_by_user_query(user_id):
    q = _activites_from_users_followed_by_user_query(user_id)
    q = q.union(_activities_from_datasets_followed_by_user_query(user_id))
    return q


def activities_from_everything_followed_by_user(user_id, limit=15):
    '''Return activities from everything that the given user is following.

    Returns all activities where the object of the activity is anything
    (user, dataset, group...) that the given user is following.

    '''
    q = _activities_from_everything_followed_by_user_query(user_id)
    return _most_recent_activities(q, limit)


def _dashboard_activity_query(user_id):
    q = _user_activity_query(user_id)
    q = q.union(_activities_from_everything_followed_by_user_query(user_id))
    return q


def dashboard_activity_list(user_id, limit=15):
    '''Return the given user's dashboard activity stream.

    Returns activities from the user's public activity stream, plus
    activities from everything that the user is following.

    This is the union of user_activity_list(user_id) and
    activities_from_everything_followed_by_user(user_id).

    '''
    q = _dashboard_activity_query(user_id)
    return _most_recent_activities(q, limit)


def _recently_changed_packages_activity_query():
    import ckan.model as model
    q = model.Session.query(model.Activity)
    q = q.filter(model.Activity.activity_type.endswith('package'))
    return q


def recently_changed_packages_activity_list(limit=15):
    q = _recently_changed_packages_activity_query()
    return _most_recent_activities(q, limit)
