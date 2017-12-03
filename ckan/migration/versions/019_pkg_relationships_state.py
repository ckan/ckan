# encoding: utf-8

from sqlalchemy import *
from migrate import *
from ckan.model.metadata import CkanMetaData
import migrate.changeset


def upgrade(migrate_engine):
    metadata = CkanMetaData()
    metadata.bind = migrate_engine

    package_relationship_table = Table('package_relationship',
                                       metadata, autoload=True)
    package_relationship_revision_table = Table('package_relationship_revision',
                                                metadata, autoload=True)

    state_column = Column('state', UnicodeText)
    state_column.create(package_relationship_table)
    state_column = Column('state', UnicodeText)
    state_column.create(package_relationship_revision_table)
    # No package relationship objects exist to migrate, so no
    # need to populate state column

def downgrade(migrate_engine):
    raise NotImplementedError()
    
