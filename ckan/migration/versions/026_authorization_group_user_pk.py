from sqlalchemy import *
from migrate import *
from datetime import datetime
import migrate.changeset
import vdm.sqlalchemy
import uuid
from sqlalchemy import types

def make_uuid():
    return unicode(uuid.uuid4())

metadata = MetaData()

user_table = Table('user', metadata, autoload=True)

authorization_group_table = Table('authorization_group', metadata, autoload=True)

authorization_group_role_table = Table('authorization_group_role', metadata,
    Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
    Column('authorization_group_id', UnicodeText, ForeignKey('authorization_group.id')),
    )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    id = Column('id', UnicodeText, primary_key=True, default=make_uuid)
    id.create(authorization_group_role_table)
    
def downgrade(migrate_engine):
    raise NotImplementedError()




