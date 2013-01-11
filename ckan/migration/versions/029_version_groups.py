import uuid

from sqlalchemy import *
from sqlalchemy import types
from migrate import *
from datetime import datetime
import migrate.changeset
from migrate.changeset.constraint import ForeignKeyConstraint

from ckan.common import json

class JsonType(types.TypeDecorator):
    '''Store data as JSON serializing on save and unserializing on use.
    '''
    impl = types.UnicodeText

    def process_bind_param(self, value, engine):
        if value is None or value == {}: # ensure we stores nulls in db not json "null"
            return None
        else:
            # ensure_ascii=False => allow unicode but still need to convert
            return unicode(json.dumps(value, ensure_ascii=False))

    def process_result_value(self, value, engine):
        if value is None:
            return None
        else:
            return json.loads(value)

    def copy(self):
        return JsonType(self.impl.length)

def make_uuid():
    return unicode(uuid.uuid4())



def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

    group_table = Table('group', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText, unique=True, nullable=False),
        Column('title', UnicodeText),
        Column('description', UnicodeText),
        Column('created', DateTime, default=datetime.now),
        )

    group_revision_table = Table('group_revision', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText, nullable=False),
        Column('title', UnicodeText),
        Column('description', UnicodeText),
        Column('created', DateTime, default=datetime.now),
        Column('state', UnicodeText),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
        Column('continuity_id', UnicodeText, ForeignKey('group.id'))
        )

    package_group_table = Table('package_group', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', UnicodeText, ForeignKey('package.id')),
        Column('group_id', UnicodeText, ForeignKey('group.id')),
        )

    package_group_revision_table = Table('package_group_revision', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', UnicodeText, ForeignKey('package.id')),
        Column('group_id', UnicodeText, ForeignKey('group.id')),
        Column('state', UnicodeText),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
        Column('continuity_id', UnicodeText, ForeignKey('package_group.id'))
        )

    group_extra_table = Table('group_extra', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('group_id', UnicodeText, ForeignKey('group.id')),
        Column('key', UnicodeText),
        Column('value', JsonType),
        )
        
    group_extra_revision_table = Table('group_extra_revision', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('group_id', UnicodeText, ForeignKey('group.id')),
        Column('key', UnicodeText),
        Column('value', JsonType),
        Column('state', UnicodeText),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
        Column('continuity_id', UnicodeText, ForeignKey('group_extra.id'))
        )

    revision_table = Table('revision', metadata, autoload=True)
    package_table = Table('package', metadata, autoload=True)

    rev_id = make_uuid()
    q = revision_table.insert(values={'id': rev_id, 
                                      'author': u'system',
                                      'message': u"Add versioning to groups, group_extras and package_groups",
                                      'timestamp': datetime.utcnow(),
                                      'state': u'active'})
    r = migrate_engine.execute(q)
    
    # handle groups: 
    
    # BUG in sqlalchemy-migrate 0.4/0.5.4: "group" isn't escaped properly when sent to 
    # postgres. 
    # cf http://code.google.com/p/sqlalchemy-migrate/issues/detail?id=32
    
    #state = Column('state', UnicodeText)
    #revision_id = Column('revision_id', UnicodeText)
    #state.create(group_table)
    #revision_id.create(group_table)
    migrate_engine.execute('ALTER TABLE "group" ADD COLUMN state TEXT')
    migrate_engine.execute('ALTER TABLE "group" ADD COLUMN revision_id TEXT')
    #q = group_table.update(values={'state': 'active',
    #                               'revision_id': rev_id})
    #migrate_engine.execute(q)
    migrate_engine.execute('UPDATE "group" SET revision_id = \'%s\', state=\'active\'' % rev_id)
    #fk = ForeignKeyConstraint(['revision_id'], [revision_table.c.id], table=group_table)
    #fk.create(migrate_engine)
    migrate_engine.execute('ALTER TABLE "group" ADD CONSTRAINT "group_revision_id_fkey" ' + \
            'FOREIGN KEY (revision_id) REFERENCES revision(id)')
    
    group_revision_table.create()
    for row in migrate_engine.execute(group_table.select()):
        group_rev = dict(row.items())
        group_rev['continuity_id'] = group_rev['id']
        
        # otherwise, this doesn't get mapped due to the bug above:
        group_rev['state'] = u'active'
        group_rev['revision_id'] = rev_id
        
        q = group_revision_table.insert(values=group_rev)
        migrate_engine.execute(q)
    
    
    state = Column('state', UnicodeText)
    revision_id = Column('revision_id', UnicodeText)
    state.create(package_group_table)
    revision_id.create(package_group_table)
    q = package_group_table.update(values={'state': u'active',
                                           'revision_id': rev_id})
    migrate_engine.execute(q)
    fk = ForeignKeyConstraint(['revision_id'], [revision_table.c.id], table=package_group_table, name = 'package_group_revision_id_fkey')
    fk.create(migrate_engine)
    package_group_revision_table.create()
    for row in migrate_engine.execute(package_group_table.select()):
        pkg_group_rev = dict(row.items())
        pkg_group_rev['continuity_id'] = pkg_group_rev['id']
        q = package_group_revision_table.insert(values=pkg_group_rev)
        migrate_engine.execute(q)
    
    state = Column('state', UnicodeText)
    revision_id = Column('revision_id', UnicodeText)
    state.create(group_extra_table)
    revision_id.create(group_extra_table)
    q = group_extra_table.update(values={'state': u'active',
                                         'revision_id': rev_id})
    migrate_engine.execute(q)
    fk = ForeignKeyConstraint(['revision_id'], [revision_table.c.id], table=group_extra_table, name='group_extra_revision_id_fkey')
    fk.create(migrate_engine)
    group_extra_revision_table.create()
    for row in migrate_engine.execute(group_extra_table.select()):
        group_extra_rev = dict(row.items())
        group_extra_rev['continuity_id'] = group_rev['id']
        q = group_extra_revision_table.insert(values=group_extra_rev)
        migrate_engine.execute(q)


def downgrade(migrate_engine):
    raise NotImplementedError()
