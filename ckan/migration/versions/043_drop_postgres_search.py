from sqlalchemy import *
from migrate import *
import migrate.changeset

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    package_search_table = Table('package_search', metadata, autoload=True)
    package_search_table.drop()
##    migrate_engine.execute('''
##DROP TABLE package_search;
##''')
