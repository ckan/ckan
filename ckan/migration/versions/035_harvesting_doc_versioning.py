# encoding: utf-8

from sqlalchemy import *
from migrate import *
import datetime
import uuid
import migrate.changeset
from migrate.changeset.constraint import PrimaryKeyConstraint
from ckan.model.types import JsonDictType

def upgrade(migrate_engine):
    metadata = MetaData(migrate_engine)

    migrate_engine.execute('''

    CREATE TABLE harvested_document_revision (
        id text NOT NULL,
        guid text,
        created timestamp without time zone,
        content text NOT NULL,
        source_id text,
        package_id text,
        state text,
        revision_id text NOT NULL,
        continuity_id text
    );

    ALTER TABLE harvested_document
        ADD COLUMN state text,
        ADD COLUMN revision_id text;

    ALTER TABLE harvested_document_revision
        ADD CONSTRAINT harvested_document_revision_pkey PRIMARY KEY (id, revision_id);

    ALTER TABLE harvested_document
        ADD CONSTRAINT harvested_document_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);

    ALTER TABLE harvested_document_revision
        ADD CONSTRAINT harvested_document_revision_continuity_id_fkey FOREIGN KEY (continuity_id) REFERENCES harvested_document(id);

    ALTER TABLE harvested_document_revision
        ADD CONSTRAINT harvested_document_revision_package_id_fkey FOREIGN KEY (package_id) REFERENCES package(id);

    ALTER TABLE harvested_document_revision
        ADD CONSTRAINT harvested_document_revision_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);

    ALTER TABLE harvested_document_revision
        ADD CONSTRAINT harvested_document_revision_source_id_fkey FOREIGN KEY (source_id) REFERENCES harvest_source(id);
    '''
    )
