from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData(migrate_engine)

def upgrade():
    package_resource = Table('package_resource', metadata, autoload=True)
    package_resource_revision = Table('package_resource_revision', metadata, autoload=True)
    column = Column('hash', UnicodeText)
    column2 = Column('hash', UnicodeText)
    column.create(package_resource)
    column2.create(package_resource_revision)

def downgrade():
    raise NotImplementedError()

