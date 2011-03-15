from sqlalchemy import *
from migrate import *
import datetime
import uuid
from migrate.changeset.constraint import PrimaryKeyConstraint

def make_uuid():
    return unicode(uuid.uuid4())

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    role_action = Table('role_action', metadata, autoload=True)
    q = role_action.insert(values={'id': make_uuid(), 'role': 'editor', 
                           'action': 'read-site', 'context': ''})
    migrate_engine.execute(q)
    q = role_action.insert(values={'id': make_uuid(), 'role': 'editor', 
                                   'action': 'read-user', 'context': ''})
    migrate_engine.execute(q)
    q = role_action.insert(values={'id': make_uuid(), 'role': 'editor', 
                                   'action': 'create-user', 'context': ''})
    migrate_engine.execute(q)
    q = role_action.insert(values={'id': make_uuid(), 'role': 'reader', 
                                   'action': 'read-site', 'context': ''})
    migrate_engine.execute(q)
    q = role_action.insert(values={'id': make_uuid(), 'role': 'reader', 
                                   'action': 'read-user', 'context': ''})
    migrate_engine.execute(q)
    q = role_action.insert(values={'id': make_uuid(), 'role': 'reader', 
                                   'action': 'create-user', 'context': ''})
    migrate_engine.execute(q)

def downgrade(migrate_engine):
    raise NotImplementedError()

