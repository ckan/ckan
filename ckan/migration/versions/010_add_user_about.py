from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData()

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    # Using sql because migrate doesn't quote reserved word 'user'
    user_sql = 'ALTER TABLE "user" ADD about TEXT'
    migrate_engine.execute(user_sql)

def downgrade(migrate_engine):
    raise NotImplementedError()
