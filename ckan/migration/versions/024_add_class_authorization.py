from sqlalchemy import *
from migrate import *
import datetime
import uuid
from migrate.changeset.constraint import PrimaryKeyConstraint

metadata = MetaData(migrate_engine)

def make_uuid():
    return unicode(uuid.uuid4())

user_object_role_table = Table('user_object_role', metadata, autoload=True)

def upgrade():
    instance = Column('instance', Boolean, default=True)
    instance.create(user_object_role_table)
    user_object_role_table.update(values={user_object_role_table.c.instance: True})

def downgrade():
    user_object_role_table.c.instance.drop()

