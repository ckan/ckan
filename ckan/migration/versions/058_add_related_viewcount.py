from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        ALTER TABLE "related"
            ADD COLUMN view_count int NOT NULL DEFAULT 0;

        UPDATE related SET view_count=0 WHERE view_count IS NULL;
    '''
    )
