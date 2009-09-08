from sqlalchemy import *
from migrate import *
import uuid

metadata = MetaData(migrate_engine)

def make_uuid():
    return unicode(uuid.uuid4())

group_table = Table('group', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.UnicodeText, unique=True, nullable=False),
        Column('title', types.UnicodeText),
        Column('description', types.UnicodeText),
)

def upgrade():
    group_table.create()

def downgrade():
    raise NotImplementedError()
