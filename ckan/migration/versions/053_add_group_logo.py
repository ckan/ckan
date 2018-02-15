# encoding: utf-8

from sqlalchemy import *
from migrate import *
from ckan.model.metadata import CkanMigrationMetaData

def upgrade(migrate_engine):
    migrate_engine.execute('''
        ALTER TABLE "group"
            ADD COLUMN image_url text;

        ALTER TABLE group_revision
            ADD COLUMN image_url text;
    '''
    )
