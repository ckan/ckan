# encoding: utf-8

from sqlalchemy import *
import sqlalchemy.schema
import uuid
from sqlalchemy.sql import select

from migrate import *
import migrate.changeset
from migrate.changeset.constraint import ForeignKeyConstraint, PrimaryKeyConstraint

metadata = MetaData()

def make_uuid():
    return unicode(uuid.uuid4())

## Tables and columns changed in the model
##     Versioned:
##        ('package', 'id'),
##        ('package_tag', ('id', 'package_id', 'tag_id')),
##        ('package_extra', ('id', 'package_id')),
##        ('package_resource', ('id', 'package_id')),
##     Versions:  
##        ('package_revision', 'id'),
##        ('package_tag_revision', ('id', 'package_id', 'tag_id')),
##        ('package_extra_revision', ('id', 'package_id')),
##        ('package_resource_revision', ('id', 'package_id')),
##     Non-versioned:
##        ('tag', 'id'),
##        ('rating', 'package_id'),
##        ('package_search', 'package_id'),
##        ('package_role', 'package_id'),
##        ('package_group', 'package_id'),

def upgrade(migrate_engine):
    global metadata
    metadata = MetaData()
    metadata.bind = migrate_engine
    primary_table_name = 'package'
    foreign_tables = ['package_revision',
                      'package_tag', 'package_tag_revision',
                      'package_extra', 'package_extra_revision',
                      'package_resource', 'package_resource_revision',
                      'rating', 'package_search',
                      'package_role', 'package_group']
    revision_table_name = 'package_revision'
    convert_to_uuids(migrate_engine, primary_table_name, foreign_tables, revision_table_name)

    primary_table_name = 'package_resource'
    foreign_tables = ['package_resource_revision']
    revision_table_name = 'package_resource_revision'
    convert_to_uuids(migrate_engine, primary_table_name, foreign_tables, revision_table_name)

    primary_table_name = 'package_tag'
    foreign_tables = ['package_tag_revision']
    revision_table_name = 'package_tag_revision'
    convert_to_uuids(migrate_engine, primary_table_name, foreign_tables, revision_table_name)

    primary_table_name = 'package_extra'
    foreign_tables = ['package_extra_revision']
    revision_table_name = 'package_extra_revision'
    convert_to_uuids(migrate_engine, primary_table_name, foreign_tables, revision_table_name)

    primary_table_name = 'tag'
    foreign_tables = ['package_tag', 'package_tag_revision']
    revision_table_name = None
    convert_to_uuids(migrate_engine, primary_table_name, foreign_tables, revision_table_name)

    drop_sequencies(migrate_engine)

def convert_to_uuids(migrate_engine, primary_table_name, foreign_tables, revision_table_name=None):
    '''Convert an id column in Primary Table to string type UUIDs.
    How it works:
       1 drop all foreign key constraints
       2 alter type of revision id and foreign keys
       3 create foreign key constraints (using cascade!)
       4 create uuids for revisions (auto cascades elsewhere!)

    @param primary_table_name - table containing the primary key id column
    @param foreign_tables - names of tables which have this same key as a
                            foreign key constraint
    @param revision_table_name - if primary_table is versioned, supply the name
          of its related revision table, so that it can be updated at the same
          time.
          '''
    #print('** Processing %s' % primary_table_name)
    #print('*** Dropping fk constraints')
    dropped_fk_constraints = drop_constraints_and_alter_types(primary_table_name, foreign_tables, revision_table_name)
    #print('*** Adding fk constraints (with cascade)')
    add_fk_constraints(migrate_engine, dropped_fk_constraints, primary_table_name)
    #print('*** Creating UUIDs')
    create_uuids(migrate_engine, primary_table_name, revision_table_name)

def drop_constraints_and_alter_types(primary_table_name, foreign_tables, revision_table_name):
    # 1 drop all foreign key constraints
    dropped_fk_constraints = []
    primary_table = Table(primary_table_name, metadata, autoload=True)
    for table_name in foreign_tables:
        table = Table(table_name, metadata, autoload=True)
        for constraint in table.constraints.copy():
            if isinstance(constraint, sqlalchemy.schema.ForeignKeyConstraint):
                foreign_key_cols = [key.column for key in constraint.elements]
                fk_col = foreign_key_cols[0]
                if fk_col.table == primary_table:
                    orig_fk = ForeignKeyConstraint(constraint.columns, foreign_key_cols, name=constraint.name, table=table)
                    orig_fk.drop()
                    dropped_fk_constraints.append((constraint.columns, foreign_key_cols, constraint.name, table.name))
                    #print 'CON', dropped_fk_constraints[-1]

    # 2 alter type of primary table id and foreign keys
                    id_col = constraint.table.columns[constraint.columns[0]]
                    id_col.alter(type=UnicodeText)

    primary_table = Table(primary_table_name, metadata, autoload=True)
    id_col = primary_table.c['id']
    id_col.alter(type=UnicodeText)

    if revision_table_name:
        # Revision table id column type changed as well
        revision_table = Table(revision_table_name, metadata, autoload=True)
        id_col = revision_table.c['id']
        id_col.alter(type=UnicodeText)

    return dropped_fk_constraints

def add_fk_constraints(migrate_engine, dropped_fk_constraints, primary_table_name):
    # 3 create foreign key constraints
    for fk_constraint in dropped_fk_constraints:
        # cascade doesn't work
        # see http://code.google.com/p/sqlalchemy-migrate/issues/detail?id=48
        # new_fk = ForeignKeyConstraint(*fk_constraint, onupdate='CASCADE')
        # new_fk = ForeignKeyConstraint(*fk_constraint)
        # new_fk.create()

        # So we create via hand ...
        constraint_columns, foreign_key_cols, constraint_name, table_name = fk_constraint
        oursql = '''ALTER TABLE %(table)s
            ADD CONSTRAINT %(fkeyname)s
            FOREIGN KEY (%(col_name)s)
            REFERENCES %(primary_table_name)s (id)
            ''' % {'table':table_name, 'fkeyname':constraint_name,
                   'col_name':constraint_columns[0],
                   'primary_table_name':primary_table_name}
        migrate_engine.execute(oursql)

def create_uuids(migrate_engine, primary_table_name, revision_table_name):
    # have changed type of cols so recreate metadata
    metadata = MetaData(migrate_engine)

    # 4 create uuids for primary entities and in related tables
    primary_table = Table(primary_table_name, metadata, autoload=True)
    if revision_table_name:
        revision_table = Table(revision_table_name, metadata, autoload=True)
    # fetchall wouldn't be optimal with really large sets of data but here <20k
    ids = [ res[0] for res in
            migrate_engine.execute(select([primary_table.c.id])).fetchall() ]
    for count,id in enumerate(ids):
        # if count % 100 == 0: print(count, id)
        myuuid = make_uuid()
        update = primary_table.update().where(primary_table.c.id==id).values(id=myuuid)
        migrate_engine.execute(update)
    if revision_table_name:
        # ensure each id in revision table match its continuity id.
        q = revision_table.update().values(id=revision_table.c.continuity_id)
        migrate_engine.execute(q)

def drop_sequencies(migrate_engine):

    sequencies = ['package_extra', 'package_extra_revision', 'package',
                  'package_resource', 'package_resource_revision',
                  'package_revision',' package_tag', 'package_tag_revision',
                  'revision', 'tag']


    for sequence in sequencies:
        migrate_engine.execute('ALTER TABLE %s ALTER COLUMN id DROP DEFAULT;' % sequence)

    for sequence in sequencies:
        migrate_engine.execute('drop sequence %s_id_seq;' % sequence)


            
def downgrade(migrate_engine):
    raise NotImplementedError()
