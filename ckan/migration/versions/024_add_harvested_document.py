from sqlalchemy import *
from migrate import *
import datetime


def upgrade(migrate_engine):
    metadata = MetaData()
    harvested_document_table = Table('harvested_document', metadata,
            Column('id', UnicodeText, primary_key=True),
            Column('created', DateTime),
            Column('url', UnicodeText, nullable=False),
            Column('content', UnicodeText, nullable=False),
    )
    metadata.bind = migrate_engine
    harvested_document_table.create()

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    harvested_document_table.drop()

