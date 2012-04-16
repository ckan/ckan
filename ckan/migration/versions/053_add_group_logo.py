from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        ALTER TABLE "group"
            ADD COLUMN logo text;

        ALTER TABLE group_revision
            ADD COLUMN logo text;
    '''
    )
