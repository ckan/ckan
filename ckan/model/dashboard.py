# encoding: utf-8

import datetime
import sqlalchemy
import ckan.model.meta as meta
from typing import Optional
from typing_extensions import Self

dashboard_table = sqlalchemy.Table('dashboard', meta.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.types.UnicodeText,
            sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
                ondelete='CASCADE'),
            primary_key=True, nullable=False),
    sqlalchemy.Column('activity_stream_last_viewed', sqlalchemy.types.DateTime,
        nullable=False),
    sqlalchemy.Column('email_last_sent', sqlalchemy.types.DateTime,
        nullable=False)
)


class Dashboard(object):
    '''Saved data used for the user's dashboard.'''
    user_id: str
    activity_stream_last_viewed: datetime.datetime
    email_last_sent: datetime.datetime

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.activity_stream_last_viewed = datetime.datetime.utcnow()
        self.email_last_sent = datetime.datetime.utcnow()

    @classmethod
    def get(cls, user_id: str) -> Optional[Self]:
        '''Return the Dashboard object for the given user_id.

        If there's no dashboard row in the database for this user_id, a fresh
        one will be created and returned.

        '''
        query = meta.Session.query(Dashboard)
        query = query.filter(Dashboard.user_id == user_id)
        return query.first()

meta.mapper(Dashboard, dashboard_table)
