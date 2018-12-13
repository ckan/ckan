# encoding: utf-8

from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
    BEGIN;
    CREATE INDEX idx_revision_author ON "revision" (author);
    CREATE INDEX idx_openid ON "user" (openid);
    CREATE INDEX "idx_user_name_index" on "user"((CASE WHEN ("user".fullname IS NULL OR "user".fullname = '') THEN "user".name ELSE "user".fullname END));
    COMMIT;
    '''
    )


