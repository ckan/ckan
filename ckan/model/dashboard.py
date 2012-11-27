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
    sqlalchemy.Column('email_last_sent', sqlalchemy.types.DateTime,
        nullable=False)
)


class Dashboard(object):
    '''Saved data used for the user's dashboard.'''

    def __init__(self, user_id):
        self.user_id = user_id
        self.activity_stream_last_viewed = datetime.datetime.now()
        self.email_last_sent = datetime.datetime.now()

    @classmethod
    def get(cls, user_id):
        '''Return the Dashboard object for the given user_id.

        If there's no dashboard row in the database for this user_id, a fresh
        one will be created and returned.

        '''
        query = meta.Session.query(Dashboard)
        query = query.filter(Dashboard.user_id == user_id)
        try:
            row = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            row = Dashboard(user_id)
            meta.Session.add(row)
            meta.Session.commit()
        return row

meta.mapper(Dashboard, dashboard_table)
