import datetime

from sqlalchemy import orm, types, Column, Table, ForeignKey

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
