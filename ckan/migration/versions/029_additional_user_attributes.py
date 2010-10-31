from sqlalchemy import *
from sqlalchemy import types
from migrate import *
from datetime import datetime
import migrate.changeset
import uuid

metadata = MetaData(migrate_engine)
    
def upgrade():
    user_sql = 'ALTER TABLE "user" ADD openid TEXT'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "user" ADD password TEXT'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "user" ADD display_name TEXT'
    migrate_engine.execute(user_sql)
    
def downgrade():
    raise NotImplementedError()