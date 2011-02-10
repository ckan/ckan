from sqlalchemy import *
from migrate import *
import migrate.changeset


def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

    package_table = Table('package', metadata, autoload=True)
    package_search_table = Table('package_search', metadata,
            Column('package_id', Integer, ForeignKey('package.id'), primary_key=True),
            )
    
    package_search_table.create()
    sql = 'ALTER TABLE package_search ADD COLUMN search_vector tsvector'
    migrate_engine.execute(sql)

    # This is not so important now and annoying to read when testing
    #print 'IMPORTANT! Now run:\n  paster create-search-index'

def downgrade(migrate_engine):
    raise NotImplementedError()
