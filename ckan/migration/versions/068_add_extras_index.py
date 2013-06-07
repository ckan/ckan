from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        create index idx_package_extra_package_id on package_extra_revision using btree (package_id, current);
    '''
    )
