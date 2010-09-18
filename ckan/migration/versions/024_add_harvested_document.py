from sqlalchemy import *
from migrate import *
import datetime

metadata = MetaData(migrate_engine)

harvested_document_table = Table('harvested_document', metadata,
        Column('id', UnicodeText, primary_key=True),
        Column('created', DateTime),
        Column('url', UnicodeText, nullable=False),
        Column('content', UnicodeText, nullable=False),
)

def upgrade():
    harvested_document_table.create()

def downgrade():
    harvested_document_table.drop()

