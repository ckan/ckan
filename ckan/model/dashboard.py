import datetime
import sqlalchemy
import meta

dashboard_table = sqlalchemy.Table('dashboard', meta.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.types.UnicodeText,
            sqlalchemy.ForeignKey('user.id', onupdate='CASCADE',
                ondelete='CASCADE'),
            primary_key=True, nullable=False),
    sqlalchemy.Column('activity_stream_last_viewed', sqlalchemy.types.DateTime,
        nullable=False),
    sqlalchemy.Column('last_activity_stream_email_notification',
        sqlalchemy.types.DateTime, nullable=False)
)


class Dashboard(object):
    '''Saved data used for the user's dashboard.'''

    def __init__(self, user_id):
        self.user_id = user_id
        self.activity_stream_last_viewed = datetime.datetime.now()
        self.last_activity_stream_email_notification = datetime.datetime.now()

    @classmethod
    def _get(cls, user_id):
        '''

        :raises: sqlalchemy.orm.exc.NoResultFound

        '''
        query = meta.Session.query(Dashboard)
        query = query.filter(Dashboard.user_id == user_id)
        row = query.one()
        return row

    @classmethod
    def get_activity_stream_last_viewed(cls, user_id):
        try:
            row = cls._get(user_id)
            return row.activity_stream_last_viewed
        except sqlalchemy.orm.exc.NoResultFound:
            # No dashboard row has been created for this user so they have no
            # activity_stream_last_viewed date. Return the oldest date we can
            # (i.e. all activities are new to this user).
            return datetime.datetime.min

    @classmethod
    def update_activity_stream_last_viewed(cls, user_id):
        try:
            row = cls._get(user_id)
            row.activity_stream_last_viewed = datetime.datetime.now()
        except sqlalchemy.orm.exc.NoResultFound:
            row = Dashboard(user_id)
            meta.Session.add(row)
        meta.Session.commit()

    @classmethod
    def get_last_activity_stream_email_notification(cls, user_id):
        try:
            row = cls._get(user_id)
            return row.activity_stream_last_viewed
        except sqlalchemy.orm.exc.NoResultFound:
            # No dashboard row has been created for this user so they have no
            # last_activity_stream_email_notification date. Return the oldest
            # date we can (i.e. all activities are new to this user).
            return datetime.datetime.min

    @classmethod
    def update_last_activity_stream_email_notification(cls, user_id):
        try:
            row = cls._get(user_id)
            row.last_activity_stream_email_notification = datetime.datetime.now()
        except sqlalchemy.orm.exc.NoResultFound:
            row = Dashboard(user_id)
            meta.Session.add(row)
        meta.Session.commit()

meta.mapper(Dashboard, dashboard_table)
