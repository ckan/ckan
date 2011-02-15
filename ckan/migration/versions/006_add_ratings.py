from sqlalchemy import *
from migrate import *
import uuid


def make_uuid():
    return unicode(uuid.uuid4())

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

    # you need to load these two for foreign keys to work 
    package_table = Table('package', metadata, autoload=True)
    user_table = Table('user', metadata, autoload=True)

    rating_table = Table('rating', metadata,
                         Column('id', UnicodeText, primary_key=True, default=make_uuid),
                         Column('user_id', UnicodeText, ForeignKey('user.id')),
                         Column('user_ip_address', UnicodeText), # alternative to user_id if not logged in
                         Column('package_id', Integer, ForeignKey('package.id')),
                         Column('rating', Float)
                         )

    rating_table.create()

def downgrade(migrate_engine):
    raise NotImplementedError()
