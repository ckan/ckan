# encoding: utf-8

from sqlalchemy import *
from migrate import *
from ckan.model.metadata import CkanMigrationMetaData

def upgrade(migrate_engine):
    metadata = CkanMigrationMetaData()
    metadata.bind = migrate_engine
    migrate_engine.execute('''
ALTER TABLE public.user
    ADD COLUMN activity_streams_email_notifications BOOLEAN DEFAULT FALSE;
    ''')
