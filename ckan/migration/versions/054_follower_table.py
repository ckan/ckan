import sqlalchemy
import ckan

follower_table = sqlalchemy.Table('follower',
        sqlalchemy.MetaData(),
    sqlalchemy.Column('follower_id', sqlalchemy.types.UnicodeText,
        nullable=False, primary_key=True),
    sqlalchemy.Column('follower_type', sqlalchemy.types.UnicodeText,
        nullable=False),
    sqlalchemy.Column('followee_id', sqlalchemy.types.UnicodeText,
        nullable=False, primary_key=True),
    sqlalchemy.Column('followee_type', sqlalchemy.types.UnicodeText,
        nullable=False),
    sqlalchemy.Column('datetime', sqlalchemy.types.DateTime, nullable=False),
)

def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    ckan.model.follower.follower_table.create()
