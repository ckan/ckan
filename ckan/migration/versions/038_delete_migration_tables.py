# encoding: utf-8

from migrate import *
from ckan.model.metadata import CkanMetaData

def upgrade(migrate_engine):

    migrate_engine.execute('''
DROP TABLE harvested_document_revision, harvested_document, harvesting_job, harvest_source;
''')



