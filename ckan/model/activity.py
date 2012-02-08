import datetime

from sqlalchemy import orm

from meta import *
from types import make_uuid
from types import JsonDictType
from core import *
from package import *

__all__ = ['Activity', 'activity_table', 
           'ActivityDetail', 'activity_detail_table',
           ]

activity_table = Table(
    'activity', metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('timestamp', types.DateTime),
    Column('user_id', types.UnicodeText),
    Column('object_id', types.UnicodeText),
    Column('revision_id', types.UnicodeText),
    Column('activity_type', types.UnicodeText),
    Column('data', JsonDictType),
    )

activity_detail_table = Table(
    'activity_detail', metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('activity_id', types.UnicodeText, ForeignKey('activity.id')),
    Column('object_id', types.UnicodeText),
    Column('object_type', types.UnicodeText),
    Column('activity_type', types.UnicodeText),
    Column('data', JsonDictType),
    )

class Activity(DomainObject):

    def __init__(self, user_id, object_id, revision_id, activity_type,
            data=None):
        self.id = make_uuid()
        self.timestamp = datetime.datetime.now()
        self.user_id = user_id
        self.object_id = object_id
        self.revision_id = revision_id
        self.activity_type = activity_type
        if data is None:
            self.data = {}
        else:
            self.data = data

mapper(Activity, activity_table)

class ActivityDetail(DomainObject):

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

mapper(ActivityDetail, activity_detail_table, properties = {
    'activity':orm.relation ( Activity, backref=orm.backref('activity_detail'))
    })
