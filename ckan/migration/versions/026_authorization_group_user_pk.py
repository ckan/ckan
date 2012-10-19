from sqlalchemy import *
from migrate import *
from datetime import datetime
import migrate.changeset
import vdm.sqlalchemy
import uuid
from sqlalchemy import types

def make_uuid():
    return unicode(uuid.uuid4())

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

    user_table = Table('user', metadata, autoload=True)

    authorization_group_table = Table('authorization_group', metadata, autoload=True)

    authorization_group_role_table = Table('authorization_group_role', metadata,
        Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
        Column('authorization_group_id', UnicodeText, ForeignKey('authorization_group.id')),
        )
##    id = Column('id', UnicodeText, primary_key=True, default=make_uuid)
##    id.create(table=authorization_group_role_table,
##              primary_key_name='blum'
###              unique_name='id'
##              )
    
def downgrade(migrate_engine):
    raise NotImplementedError()




