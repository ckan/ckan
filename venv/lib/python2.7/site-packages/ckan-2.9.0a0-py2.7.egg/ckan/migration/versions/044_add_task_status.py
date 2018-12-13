# encoding: utf-8

from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        CREATE TABLE task_status (
            id text NOT NULL,
            entity_id text NOT NULL,
            entity_type text NOT NULL,
            task_type text NOT NULL,
            "key" text NOT NULL,
            "value" text NOT NULL,
            "state" text,
            "error" text,
            last_updated timestamp without time zone
        );

        ALTER TABLE task_status
            ADD CONSTRAINT task_status_pkey PRIMARY KEY (id);

        ALTER TABLE task_status
            ADD CONSTRAINT task_status_entity_id_task_type_key_key UNIQUE (entity_id, task_type, key);
    '''
    )
