# encoding: utf-8

from sqlalchemy import *
from sqlalchemy import types
from migrate import *
from ckan.model.metadata import CkanMetaData
from datetime import datetime
import migrate.changeset
import uuid

    
def upgrade(migrate_engine):
    metadata = CkanMetaData(migrate_engine)
    user_sql = 'ALTER TABLE package_resource ADD COLUMN extras text'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE package_resource_revision ADD COLUMN extras text'
    migrate_engine.execute(user_sql)

def downgrade():
    raise NotImplementedError()

