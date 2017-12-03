# encoding: utf-8

from sqlalchemy import *
from migrate import *
from ckan.model.metadata import CkanMetaData

def upgrade(migrate_engine):
    metadata = CkanMetaData()
    metadata.bind = migrate_engine
    migrate_engine.execute('''
ALTER TABLE dashboard
    ADD COLUMN email_last_sent timestamp without time zone NOT NULL DEFAULT LOCALTIMESTAMP;
    ''')
