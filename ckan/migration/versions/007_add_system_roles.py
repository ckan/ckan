# encoding: utf-8

from sqlalchemy import *
from migrate import *
from ckan.model.metadata import CkanMetaData
import uuid




def upgrade(migrate_engine):
    metadata = CkanMetaData()
    metadata.bind = migrate_engine

    user_object_role_table = Table('user_object_role', metadata, autoload=True)

    # authorization tables
    system_role_table = Table('system_role', metadata,
               Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
               )
        
    system_role_table.create()

    # you can now add system administrators
    # e.g. paster create-sysadmin http://bgates.openid.com/

def downgrade(migrate_engine):
    raise NotImplementedError()
