from sqlalchemy import *
from migrate import *
import uuid

metadata = MetaData()

def make_uuid():
    return unicode(uuid.uuid4())

user_table = Table('user', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText),
        Column('apikey', UnicodeText, default=make_uuid)
        )

apikey_table = Table('apikey', metadata, autoload=True)

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    user_table.create()
    apikey_table.drop()

def downgrade(migrate_engine):
    raise NotImplementedError()

