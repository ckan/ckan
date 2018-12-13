# encoding: utf-8

from sqlalchemy import *
from migrate import *
import migrate.changeset

    
def upgrade(migrate_engine):
    metadata = MetaData()
    harvested_source_table = Table('harvest_source', metadata,
        Column('status', UnicodeText, nullable=False),
        )
    metadata.bind = migrate_engine
    harvested_source_table.c.status.drop()

def downgrade():
    raise NotImplementedError()

