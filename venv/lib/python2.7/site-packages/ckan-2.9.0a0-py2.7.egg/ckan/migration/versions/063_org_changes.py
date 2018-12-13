# encoding: utf-8

from migrate import *

def upgrade(migrate_engine):

    update_schema = '''
BEGIN;

ALTER TABLE "user"
    ADD COLUMN sysadmin boolean DEFAULT FALSE;

ALTER TABLE package
    ADD COLUMN owner_org TEXT,
    ADD COLUMN private boolean DEFAULT FALSE;

ALTER TABLE package_revision
    ADD COLUMN owner_org TEXT,
    ADD COLUMN private boolean DEFAULT FALSE;


ALTER TABLE "group"
    ADD COLUMN is_organization boolean DEFAULT FALSE;

ALTER TABLE group_revision
    ADD COLUMN is_organization boolean DEFAULT FALSE;

UPDATE "user" SET sysadmin=true WHERE id in ( SELECT user_id FROM user_object_role WHERE role='admin' AND context='System');

COMMIT;

'''
    migrate_engine.execute(update_schema)
