from sqlalchemy import *
from sqlalchemy import types
from migrate import *
from datetime import datetime
import migrate.changeset
import uuid

metadata = MetaData(migrate_engine)

def make_uuid():
    return unicode(uuid.uuid4())

user_table = Table('user', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('name', UnicodeText),
    Column('openid', UnicodeText),
    Column('password', UnicodeText),
    Column('fullname', UnicodeText),
    Column('apikey', UnicodeText, default=make_uuid),
    Column('created', DateTime, default=datetime.now),
    Column('about', UnicodeText),
    )
    
def upgrade():
    for row in migrate_engine.execute(user_table.select()):
        user = dict(row.items())
        name = user.get('name').lower().strip()
        if name.startswith('http://') or name.startswith('https://'):
            user['openid'] = name
        q = user_table.update(user_table.c.id==user.get('id'), 
                              values=user)
        migrate_engine.execute(q)
    
def downgrade():
    raise NotImplementedError()
