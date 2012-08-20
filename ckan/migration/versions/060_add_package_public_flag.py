from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
BEGIN;
ALTER TABLE "package"
	ADD COLUMN "public" integer default 1;
ALTER TABLE "package_revision"
	ADD COLUMN "public" integer default 1;

update "package" set public = 1;
update "package_revision" set public = 1;

COMMIT;
    '''
    )
