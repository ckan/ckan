# encoding: utf-8

from sqlalchemy import *
from migrate import *
from ckan.model.metadata import CkanMigrationMetaData
import migrate.changeset


def upgrade(migrate_engine):
    metadata = CkanMigrationMetaData()
    metadata.bind = migrate_engine
    package_resource = Table('package_resource', metadata, autoload=True)
    column = Column('hash', UnicodeText)
    column.create(package_resource)

def downgrade(migrate_engine):
    raise NotImplementedError()

