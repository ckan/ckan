from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    migrate_engine.execute('''
CREATE TABLE activity (
	id text NOT NULL,
	timestamp timestamp without time zone,
	user_id text,
	object_id text,
	revision_id text,
	activity_type text,
	data text
);

CREATE TABLE activity_detail (
	id text NOT NULL,
	activity_id text NOT NULL,
	object_id text,
	object_type text,
	activity_type text,
	data text
);

ALTER TABLE activity
	ADD CONSTRAINT activity_pkey PRIMARY KEY (id);

ALTER TABLE activity_detail
	ADD CONSTRAINT activity_detail_pkey PRIMARY KEY (id);

ALTER TABLE activity_detail
	ADD CONSTRAINT activity_detail_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES activity(id);
    ''')
