from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    migrate_engine.execute('''
BEGIN;
CREATE TABLE related (
	id text NOT NULL,
	type text NOT NULL,
	title text,
	description text,
	image_url text,
	url text,
	created timestamp without time zone,
	owner_id text
);

CREATE TABLE related_dataset (
	id text NOT NULL,
	dataset_id text NOT NULL,
	related_id text NOT NULL,
	status text
);

ALTER TABLE related
	ADD CONSTRAINT related_pkey PRIMARY KEY (id);

ALTER TABLE related_dataset
	ADD CONSTRAINT related_dataset_pkey PRIMARY KEY (id);

ALTER TABLE related_dataset
	ADD CONSTRAINT related_dataset_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES package(id);

ALTER TABLE related_dataset
	ADD CONSTRAINT related_dataset_related_id_fkey FOREIGN KEY (related_id) REFERENCES related(id);
COMMIT;
    '''
    )
