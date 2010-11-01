from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData(migrate_engine)

harvested_source_table = Table('harvest_source', metadata,
    Column('status', UnicodeText, nullable=False),
)

def upgrade():
    harvest_source_table.c.status.drop()

def downgrade():
    raise NotImplementedError()

