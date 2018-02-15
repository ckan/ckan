# encoding: utf-8

from sqlalchemy import *
from migrate import *
from ckan.model.metadata import CkanMigrationMetaData
import migrate.changeset


def upgrade(migrate_engine):
    metadata = CkanMigrationMetaData()
    metadata.bind = migrate_engine
    # Using sql because migrate doesn't quote reserved word 'user'
    user_sql = 'ALTER TABLE "user" ADD about TEXT'
    migrate_engine.execute(user_sql)

def downgrade(migrate_engine):
    raise NotImplementedError()
