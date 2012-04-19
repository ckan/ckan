import sqlalchemy
from meta import metadata

# FIXME: Should follower_type and followeee_type be part of the primary key too?
follower_table = sqlalchemy.Table('follower',
        metadata,
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
