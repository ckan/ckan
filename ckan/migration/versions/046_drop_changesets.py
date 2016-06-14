# encoding: utf-8

from sqlalchemy import *
from migrate import *
import migrate.changeset

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    for table_name in ['change', 'changemask', 'changeset']:
        table = Table(table_name, metadata, autoload=True)
        table.drop()
