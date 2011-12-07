from sqlalchemy import *  
from migrate import * 

def upgrade(migrate_engine):
    metadata = MetaData()      
    metadata.bind = migrate_engine    
     
    migrate_engine.execute(
    '''
    ALTER TABLE package
        ADD COLUMN type_name text;

    ALTER TABLE package_revision
        ADD COLUMN type_name text;
    '''
    )
