from sqlalchemy import *
from sqlalchemy import types
from migrate import *
from datetime import datetime
import migrate.changeset
import uuid

    
def upgrade(migrate_engine):
    metadata = MetaData(migrate_engine)
    user_sql = 'ALTER TABLE package_resource ADD COLUMN extras text'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE package_resource_revision ADD COLUMN extras text'
    migrate_engine.execute(user_sql)

def downgrade():
    raise NotImplementedError()

