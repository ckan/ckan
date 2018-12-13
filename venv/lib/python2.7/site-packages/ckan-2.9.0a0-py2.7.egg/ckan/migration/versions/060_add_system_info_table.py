# encoding: utf-8

from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    meta = MetaData()


    system_info_table = Table('system_info', meta,
            Column('id', Integer() ,  primary_key=True, nullable=False),
            Column('key', Unicode(100), unique=True, nullable=False),
            Column('value', UnicodeText),
            Column('revision_id', UnicodeText, ForeignKey('revision.id'))
        )

    system_info_revision_table = Table('system_info_revision', meta,
            Column('id', Integer() ,  primary_key=True, nullable=False),
            Column('key', Unicode(100), unique=True, nullable=False),
            Column('value', UnicodeText),
            Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
            Column('continuity_id', Integer(), ForeignKey('system_info.id') ),
        )


    meta.bind = migrate_engine
    revision_table = Table('revision', meta, autoload=True)

    meta.create_all()
