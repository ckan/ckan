from sqlalchemy import *
from migrate import *
import datetime
import uuid
from migrate.changeset.constraint import PrimaryKeyConstraint


def make_uuid():
    return unicode(uuid.uuid4())

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    authorization_group_user_table = Table('authorization_group_user',
                                           metadata, autoload=True)

    try:
        ##check if id column already exists
        authorization_group_user_table.c["id"]
        return
    except KeyError:
        pass


    id_col = Column('id', UnicodeText, primary_key=True, default=make_uuid)
    id_col.create(authorization_group_user_table,
                  primary_key_name='authorization_group_user_pkey')

def downgrade(migrate_engine):
    raise NotImplementedError()
