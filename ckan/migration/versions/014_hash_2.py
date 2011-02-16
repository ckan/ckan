from sqlalchemy import *
from migrate import *
import migrate.changeset


def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    # When adding a column to a revisioned object, need to add it to it's
    # counterpart revision object too. Here is the counter-part for that in
    # 013_add_hash.py
    package_resource_revision = Table('package_resource_revision', metadata, autoload=True)
    column = Column('hash', UnicodeText)
    column.create(package_resource_revision)

def downgrade(migrate_engine):
    raise NotImplementedError()
