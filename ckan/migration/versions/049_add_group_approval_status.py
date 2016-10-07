# encoding: utf-8

from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
BEGIN;
ALTER TABLE "group"
	ADD COLUMN approval_status text;

ALTER TABLE group_revision
	ADD COLUMN approval_status text;

update "group" set approval_status = 'approved';
update group_revision set approval_status = 'approved';

COMMIT;
    '''
    )
