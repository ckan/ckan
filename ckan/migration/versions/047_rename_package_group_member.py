from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
BEGIN;
alter table package_group RENAME to member;
alter table package_group_revision RENAME to member_revision;
alter table member RENAME column package_id to table_id;
alter table member_revision RENAME column package_id to table_id;

alter table member ALTER column table_id set NOT NULL;
alter table member_revision ALTER column table_id set NOT NULL;

ALTER TABLE member_revision
	DROP CONSTRAINT package_group_revision_pkey;

ALTER TABLE member_revision
	DROP CONSTRAINT package_group_revision_continuity_id_fkey;

ALTER TABLE member_revision
	DROP CONSTRAINT package_group_revision_group_id_fkey;

ALTER TABLE member_revision
	DROP CONSTRAINT package_group_revision_package_id_fkey;

ALTER TABLE member_revision
	DROP CONSTRAINT package_group_revision_revision_id_fkey;

ALTER TABLE "member"
	DROP CONSTRAINT package_group_pkey;

ALTER TABLE "member"
	DROP CONSTRAINT package_group_group_id_fkey;

ALTER TABLE "member"
	DROP CONSTRAINT package_group_package_id_fkey;

ALTER TABLE "member"
	DROP CONSTRAINT package_group_revision_id_fkey;


ALTER TABLE "member"
	ADD COLUMN table_name text;
ALTER TABLE "member"
	ADD COLUMN capacity text;

ALTER TABLE "member_revision"
	ADD COLUMN table_name text;
ALTER TABLE "member_revision"
	ADD COLUMN capacity text;

ALTER TABLE "member"
	ADD CONSTRAINT member_pkey PRIMARY KEY (id);

ALTER TABLE member_revision
	ADD CONSTRAINT member_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE "member"
	ADD CONSTRAINT member_group_id_fkey FOREIGN KEY (group_id) REFERENCES "group"(id);

ALTER TABLE "member"
	ADD CONSTRAINT member_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);

ALTER TABLE member_revision
	ADD CONSTRAINT member_revision_continuity_id_fkey FOREIGN KEY (continuity_id) REFERENCES member(id);

ALTER TABLE member_revision
	ADD CONSTRAINT member_revision_group_id_fkey FOREIGN KEY (group_id) REFERENCES "group"(id);

ALTER TABLE member_revision
	ADD CONSTRAINT member_revision_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);

ALTER TABLE "group"
	ADD COLUMN "type" text;
ALTER TABLE "group_revision"
	ADD COLUMN "type" text;

update member set table_name = 'package', capacity = 'member';
update member_revision set table_name = 'package', capacity = 'member';

update "group" set type = 'group';
update group_revision set type = 'group';


ALTER TABLE "member"
	ALTER COLUMN  table_name set not null;
ALTER TABLE "member"
	ALTER COLUMN  capacity set not null;

ALTER TABLE member_revision
	ALTER COLUMN table_name set not null;
ALTER TABLE "member_revision"
	ALTER COLUMN capacity set not null;

ALTER TABLE "group"
	ALTER COLUMN "type" set not null;
ALTER TABLE "group_revision"
	ALTER COLUMN "type" set not null;

ALTER TABLE "package"
	ADD COLUMN "type" text;
ALTER TABLE "package_revision"
	ADD COLUMN "type" text;
	

COMMIT;
    '''
    )
