from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        BEGIN;

        CREATE TABLE data_cache (
            id text NOT NULL,
            object_id text,
            key text NOT NULL,
            value text,
            created timestamp without time zone
        );

        CREATE INDEX idx_data_cache_object ON data_cache (object_id);
        CREATE INDEX idx_data_cache_object_key ON data_cache (object_id,key);

        COMMIT;
    '''
    )
