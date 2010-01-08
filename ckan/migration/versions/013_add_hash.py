from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData(migrate_engine)

def upgrade():
    package_resource = Table('package_resource', metadata, autoload=True)
    column = Column('hash', UnicodeText)
    column.create(package_resource)

def downgrade():
    raise NotImplementedError()

