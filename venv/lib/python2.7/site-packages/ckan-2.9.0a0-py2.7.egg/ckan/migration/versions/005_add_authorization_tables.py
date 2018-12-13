# encoding: utf-8

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
    group_table = Table('group', metadata, autoload=True)
    user_table = Table('user', metadata, autoload=True)

    # authorization tables
    role_action_table = Table('role_action', metadata,
               Column('id', UnicodeText, primary_key=True, default=make_uuid),
               Column('role', UnicodeText),
               Column('context', UnicodeText, nullable=False),
               Column('action', UnicodeText),
               )

    user_object_role_table = Table('user_object_role', metadata,
               Column('id', UnicodeText, primary_key=True, default=make_uuid),
               Column('user_id', UnicodeText, ForeignKey('user.id')),
               Column('context', UnicodeText, nullable=False),
               Column('role', UnicodeText)
               )

    package_role_table = Table('package_role', metadata,
               Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
               Column('package_id', Integer, ForeignKey('package.id')),
               )

    group_role_table = Table('group_role', metadata,
               Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
               Column('group_id', UnicodeText, ForeignKey('group.id')),
               )
    
    role_action_table.create()
    user_object_role_table.create()
    package_role_table.create()
    group_role_table.create()

    # Not Good to use model here. TODO: refactor this.
    # import ckan.model as model
    # model.repo.init_db()
    # call this explicitly elsewhere
    # model.give_all_packages_default_user_roles()

def downgrade(migrate_engine):
    raise NotImplementedError()
