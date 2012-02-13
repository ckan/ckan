from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        ALTER TABLE tag
            DROP CONSTRAINT tag_name_key;

        CREATE TABLE vocabulary (
            id text NOT NULL,
            name character varying(100) NOT NULL
        );

        ALTER TABLE tag
            ADD COLUMN vocabulary_id character varying(100);

        ALTER TABLE vocabulary
            ADD CONSTRAINT vocabulary_pkey PRIMARY KEY (id);

        ALTER TABLE tag
            ADD CONSTRAINT tag_name_vocabulary_id_key UNIQUE (name, vocabulary_id);

        ALTER TABLE tag
            ADD CONSTRAINT tag_vocabulary_id_fkey FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id);

        ALTER TABLE vocabulary
            ADD CONSTRAINT vocabulary_name_key UNIQUE (name);
    '''
    )
