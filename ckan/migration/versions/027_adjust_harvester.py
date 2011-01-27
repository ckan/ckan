from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData()

harvested_document_table = Table('harvested_document', metadata,
    Column('url', UnicodeText, nullable=False),
    Column('guid', UnicodeText, default=''),
    Column('source_id', UnicodeText, ForeignKey('harvest_source.id')),
    Column('package_id', UnicodeText, ForeignKey('package.id')),
)

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    harvested_document_table.c.url.drop()
    harvested_document_table.c.guid.create()
    harvested_document_table.c.source_id.create()
    harvested_document_table.c.package_id.create()

def downgrade(migrate_engine):
    raise NotImplementedError()

