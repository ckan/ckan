from sqlalchemy import *
from migrate import *
from migrate.changeset.constraint import UniqueConstraint

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    user_table = Table('user', metadata, autoload=True)
#    name_column = user_table.c.name
    unique_name_constraint = UniqueConstraint('name', table=user_table)
    unique_name_constraint.create()
