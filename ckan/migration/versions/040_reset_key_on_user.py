# encoding: utf-8

from sqlalchemy import *
from migrate import *
from ckan.model.metadata import CkanMigrationMetaData

def upgrade(migrate_engine):
    metadata = CkanMigrationMetaData()
    metadata.bind = migrate_engine
    user_table = Table('user', metadata, autoload=True)
    reset_key_col = Column('reset_key', UnicodeText)
    reset_key_col.create(user_table)

def downgrade(migrate_engine):
    raise NotImplementedError()

