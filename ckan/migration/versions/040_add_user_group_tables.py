from migrate import *

def upgrade(migrate_engine):

    migrate_engine.execute('''

BEGIN;

CREATE TABLE user_group (
	id text NOT NULL,
	name text NOT NULL,
	parent_id text
);

CREATE TABLE user_group_extra (
	id text NOT NULL,
	user_group_id text NOT NULL,
	"key" text NOT NULL,
	"value" text NOT NULL
);

CREATE TABLE user_group_package (
	id text NOT NULL,
	user_group_id text NOT NULL,
	package_id text NOT NULL,
	capacity text
);

CREATE TABLE user_group_user (
	id text NOT NULL,
	user_group_id text NOT NULL,
	user_id text NOT NULL,
	capacity text
);


ALTER TABLE user_group
	ADD CONSTRAINT user_group_pkey PRIMARY KEY (id);

ALTER TABLE user_group_extra
	ADD CONSTRAINT user_group_extra_pkey PRIMARY KEY (id);

ALTER TABLE user_group_package
	ADD CONSTRAINT user_group_package_pkey PRIMARY KEY (id);

ALTER TABLE user_group_user
	ADD CONSTRAINT user_group_user_pkey PRIMARY KEY (id);



ALTER TABLE user_group_extra
	ADD CONSTRAINT user_group_extra_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);

ALTER TABLE user_group_package
	ADD CONSTRAINT user_group_package_package_id_fkey FOREIGN KEY (package_id) REFERENCES package(id);

ALTER TABLE user_group_package
	ADD CONSTRAINT user_group_package_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);

ALTER TABLE user_group_user
	ADD CONSTRAINT user_group_user_user_group_id_fkey FOREIGN KEY (user_group_id) REFERENCES user_group(id);

ALTER TABLE user_group_user
	ADD CONSTRAINT user_group_user_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);

COMMIT;
''')
