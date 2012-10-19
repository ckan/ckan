from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    user_table = Table('user', metadata, autoload=True)
    reset_key_col = Column('reset_key', UnicodeText)
    reset_key_col.create(user_table)

def downgrade(migrate_engine):
    raise NotImplementedError()

