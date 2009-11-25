from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData(migrate_engine)

def upgrade():
    # Using sql because migrate doesn't quote reserved word 'user'
    user_sql = 'ALTER TABLE "user" ADD about TEXT'
    migrate_engine.execute(user_sql)

def downgrade():
    raise NotImplementedError()
