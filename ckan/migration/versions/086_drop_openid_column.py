# encoding: utf-8

from ckan.model.metadata import CkanMigrationMetaData


def upgrade(migrate_engine):
    metadata = CkanMigrationMetaData()
    metadata.bind = migrate_engine
    migrate_engine.execute('''
ALTER TABLE "user"
    DROP COLUMN openid;
    ''')
