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

    authorization_group_table = Table('authorization_group', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText),
        Column('created', DateTime, default=datetime.now),
        )

    authorization_group_user_table = Table('authorization_group_user', metadata,
        Column('authorization_group_id', UnicodeText, ForeignKey('authorization_group.id'), nullable=False),
        Column('user_id', UnicodeText, ForeignKey('user.id'), nullable=False)
        )

    # make user nullable: 
    user_object_role_table = Table('user_object_role', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('user_id', UnicodeText, ForeignKey('user.id'), nullable=True),
        Column('context', UnicodeText, nullable=False),
        Column('role', UnicodeText)
        )

    authorization_group_role_table = Table('authorization_group_role', metadata,
        Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
        Column('authorization_group_id', UnicodeText, ForeignKey('authorization_group.id')),
        )
    
    authorization_group_table.create()
    authorization_group_user_table.create()
    authorization_group_role_table.create()
    authorization_group_id = Column('authorized_group_id', UnicodeText, 
                                    ForeignKey('authorization_group.id'), nullable=True)
    authorization_group_id.create(user_object_role_table)

def downgrade(migrate_engine):
    raise NotImplementedError()




