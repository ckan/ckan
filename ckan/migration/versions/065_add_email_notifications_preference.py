from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    migrate_engine.execute('''
ALTER TABLE public.user
    ADD COLUMN activity_streams_email_notifications BOOLEAN DEFAULT FALSE;
    ''')
