from sqlalchemy import *
from migrate import *
import datetime
import uuid
import migrate.changeset
from migrate.changeset.constraint import PrimaryKeyConstraint
from ckan.model.types import JsonDictType

def make_uuid():
    return unicode(uuid.uuid4())

def upgrade(migrate_engine):

    metadata = MetaData(migrate_engine)

    package = Table('package', metadata, autoload=True)

    resource = Table(
        'package_resource', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', UnicodeText, ForeignKey('package.id')),
        Column('url', UnicodeText, nullable=False),
        Column('format', UnicodeText),
        Column('description', UnicodeText),
        Column('hash', UnicodeText),
        Column('position', Integer),
        Column('extras', JsonDictType),
        Column('state', UnicodeText),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
        )

    resource_revision = Table(
        'package_resource_revision', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', UnicodeText),
        Column('url', UnicodeText, nullable=False),
        Column('format', UnicodeText),
        Column('description', UnicodeText),
        Column('hash', UnicodeText),
        Column('position', Integer),
        Column('extras', JsonDictType),
        Column('state', UnicodeText),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
        Column('continuity_id', UnicodeText, ForeignKey('package_resource.id'))
        )

    resource_group = Table(
        'resource_group', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', UnicodeText, ForeignKey('package.id')),
        Column('label', UnicodeText),
        Column('sort_order', UnicodeText),
        Column('extras', JsonDictType),
        Column('state', UnicodeText),
        Column('revision_id', UnicodeText, ForeignKey('revision.id')),
        )

    resource_group_revision = Table(
        'resource_group_revision', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', UnicodeText, ForeignKey('package.id')),
        Column('label', UnicodeText),
        Column('sort_order', UnicodeText),
        Column('extras', JsonDictType),
        Column('state', UnicodeText),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
        Column('continuity_id', UnicodeText, ForeignKey('resource_group.id'))
        )
    
    resource_count = migrate_engine.execute('''select count(*) from package_resource''').first()[0]
    package_count = migrate_engine.execute('''select count(*) from package''').first()[0]


    # change field names
    resource.c.package_id.alter(name = 'resource_group_id')
    resource_revision.c.package_id.alter(name = 'resource_group_id')

    # rename tables
    resource.rename('resource')
    resource_revision.rename('resource_revision')

    # make new tables
    metadata.create_all(migrate_engine)

    # drop all constaints
    migrate_engine.execute('''
ALTER TABLE resource_revision
	DROP CONSTRAINT package_resource_revision_pkey;

ALTER TABLE resource
	DROP CONSTRAINT package_resource_revision_id_fkey;

ALTER TABLE resource_revision
	DROP CONSTRAINT package_resource_revision_continuity_id_fkey;

ALTER TABLE resource_revision
	DROP CONSTRAINT package_resource_revision_package_id_fkey;

ALTER TABLE resource_revision
	DROP CONSTRAINT package_resource_revision_revision_id_fkey;

ALTER TABLE resource
	DROP CONSTRAINT package_resource_pkey;

ALTER TABLE resource
	DROP CONSTRAINT package_resource_package_id_fkey;
''')


    # do data transfer
    # give resource group a hashed version of package uuid 
    # so that we can use the same hash calculation on  
    # the resource and resource revision table
    migrate_engine.execute('''
insert into resource_group 
    select 
        %s, id, 'default', null, null, state, revision_id
    from
        package;
''' %  make_new_uuid("id")
)

    migrate_engine.execute('''
insert into resource_group_revision
    select 
        id, package_id, 'default', null, null, state, revision_id, id
    from
        resource_group;
'''
)

    ## update resource table with new ids generated from the
    migrate_engine.execute('update resource set resource_group_id = %s' 
                           % make_new_uuid('resource_group_id'))

    migrate_engine.execute('update resource_revision set resource_group_id = %s' 
                           % make_new_uuid('resource_group_id'))

##add back contraints

    migrate_engine.execute('''
ALTER TABLE resource
	ADD CONSTRAINT resource_pkey PRIMARY KEY (id);

ALTER TABLE resource_revision
	ADD CONSTRAINT resource_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE resource
	ADD CONSTRAINT resource_resource_group_id_fkey FOREIGN KEY (resource_group_id) REFERENCES resource_group(id);

ALTER TABLE resource
	ADD CONSTRAINT resource_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);

ALTER TABLE resource_revision
	ADD CONSTRAINT resource_revision_continuity_id_fkey FOREIGN KEY (continuity_id) REFERENCES resource(id);

ALTER TABLE resource_revision
	ADD CONSTRAINT resource_revision_resource_group_id_fkey FOREIGN KEY (resource_group_id) REFERENCES resource_group(id);

ALTER TABLE resource_revision
	ADD CONSTRAINT resource_revision_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);
''')

    resource_count_after = migrate_engine.execute('''select count(*) from resource''').first()[0]
    resource_group_after = migrate_engine.execute('''select count(*) from resource_group''').first()[0]
    package_count_after = migrate_engine.execute('''select count(*) from package''').first()[0]

    all_joined = migrate_engine.execute('''select count(*) from package p 
                                           join resource_group rg on rg.package_id = p.id
                                           join resource r on r.resource_group_id = rg.id
                                        ''').first()[0]

    all_uuids = migrate_engine.execute('''
                                     select count(*) from 
                                     (select id from resource union 
                                     select id from resource_group union 
                                     select id from package) sub
                                     ''').first()[0]

    assert resource_count_after == resource_count 
    assert resource_group_after == package_count 
    assert package_count_after == package_count 

    ## this makes sure all uuids are unique (union dedupes)
    assert all_uuids == resource_count + package_count * 2 

    ## this makes sure all uuids are unique (union dedupes)
    assert all_joined == resource_count 



def make_new_uuid(column_name):

    out = '''substring(md5(%s), 1, 8)  || '-' ||
             substring(md5(%s), 9, 4)  || '-' ||
             substring(md5(%s), 13, 4)  || '-' ||        
             substring(md5(%s), 17, 4)  || '-' ||   
             substring(md5(%s), 21, 12)'''

    return out % tuple([column_name] * 5)





def downgrade(migrate_engine):
    raise NotImplementedError()
