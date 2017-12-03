# encoding: utf-8

from ckan.model.metadata import CkanMetaData


def upgrade(migrate_engine):
    metadata = CkanMetaData()
    metadata.bind = migrate_engine
    migrate_engine.execute('''
ALTER TABLE "user"
    DROP COLUMN openid;
    ''')
