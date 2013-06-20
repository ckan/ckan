from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        BEGIN;
        CREATE INDEX ON activity_detail(activity_id);
        CREATE INDEX ON activity(user_id);
        COMMIT;
    '''
    )
