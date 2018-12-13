# encoding: utf-8

from sqlalchemy import *
from sqlalchemy import types
from migrate import *
from datetime import datetime
import migrate.changeset
import uuid

    
def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    user_sql = 'ALTER TABLE "user" ADD openid TEXT'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "user" ADD password TEXT'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "user" ADD fullname TEXT'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "user" ADD email TEXT'
    migrate_engine.execute(user_sql)
    
def downgrade(migrate_engine):
    raise NotImplementedError()
