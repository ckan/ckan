from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute(
    '''
    begin;
    ALTER TABLE resource
    ADD COLUMN name text,
    ADD COLUMN resource_type text,
    ADD COLUMN mimetype text,
    ADD COLUMN mimetype_inner text,
    ADD COLUMN "size" bigint,
    ADD COLUMN last_modified timestamp without time zone,
    ADD COLUMN cache_url text,
    ADD COLUMN cache_last_updated timestamp without time zone,
    ADD COLUMN webstore_url text,
    ADD COLUMN webstore_last_updated timestamp without time zone;

    ALTER TABLE resource_revision
    ADD COLUMN name text,
    ADD COLUMN resource_type text,
    ADD COLUMN mimetype text,
    ADD COLUMN mimetype_inner text,
    ADD COLUMN "size" bigint,
    ADD COLUMN last_modified timestamp without time zone,
    ADD COLUMN cache_url text,
    ADD COLUMN cache_last_updated timestamp without time zone,
    ADD COLUMN webstore_url text,
    ADD COLUMN webstore_last_updated timestamp without time zone;
    commit;
    '''
    )
