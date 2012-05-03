from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        ALTER TABLE "related"
            ADD COLUMN view_count INT NOT NULL DEFAULT 0;

        ALTER TABLE "related"
            ADD COLUMN featured INT NOT NULL DEFAULT 0;

        UPDATE related SET view_count=0, featured=0 WHERE view_count IS NULL;
    '''
    )
