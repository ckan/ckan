# encoding: utf-8

from sqlalchemy import *
import sqlalchemy.schema
import uuid

from migrate import *
import migrate.changeset
from migrate.changeset.constraint import ForeignKeyConstraint, PrimaryKeyConstraint

metadata = None

def make_uuid():
    return unicode(uuid.uuid4())

# 1 drop all foreign key constraints
# 2 alter type of revision id and foreign keys
# 3 create foreign key constraints (using cascade!)
# 4 create uuids for revisions (auto cascades elsewhere!)
def upgrade(migrate_engine):
    global metadata
    metadata = MetaData()
    metadata.bind = migrate_engine
    dropped_fk_constraints = drop_constraints_and_alter_types()
    upgrade2(migrate_engine, dropped_fk_constraints)

def drop_constraints_and_alter_types():
    # 1 drop all foreign key constraints
    dropped_fk_constraints = []
    revision_table = Table('revision', metadata, autoload=True)
    foreign_tables = ['package', 'package_tag', 'package_revision', 'package_tag_revision', 'package_extra', 'package_extra_revision', ]
    for table_name in foreign_tables:
        table = Table(table_name, metadata, autoload=True)
        for constraint in table.constraints.copy():
            if isinstance(constraint, sqlalchemy.schema.ForeignKeyConstraint):
                foreign_key_cols = [key.column for key in constraint.elements]
                fk_col = foreign_key_cols[0]
                if fk_col.table == revision_table:
                    orig_fk = ForeignKeyConstraint(constraint.columns, foreign_key_cols, name=constraint.name, table=table)
                    orig_fk.drop()
                    dropped_fk_constraints.append((constraint.columns, foreign_key_cols, constraint.name, table.name))

    # 2 alter type of revision id and foreign keys
                    # Sanity check
                    if len(constraint.columns.keys()) != 1:
                        raise ValueError()
                    id_col = constraint.table.columns[constraint.columns.keys()[0]]
                    id_col.alter(type=UnicodeText)

    revision_table = Table('revision', metadata, autoload=True)
    id_col = revision_table.c['id']
    id_col.alter(type=UnicodeText,
                 )

    return dropped_fk_constraints

def upgrade2(migrate_engine, dropped_fk_constraints):
    # have changed type of cols so recreate metadata
    metadata = MetaData(migrate_engine)

    # 3 create foreign key constraints
    for fk_constraint in dropped_fk_constraints:
        # cascade doesn't work
        # see http://code.google.com/p/sqlalchemy-migrate/issues/detail?id=48
        # new_fk = ForeignKeyConstraint(*fk_constraint, onupdate='CASCADE')
        # new_fk = ForeignKeyConstraint(*fk_constraint)
        # new_fk.create()

        # So we create via hand ...
        constraint_columns, foreign_key_cols, constraint_name, table_name = fk_constraint
        # Sanity check
        if len(constraint_columns.keys()) != 1:
            raise ValueError()

        oursql = '''ALTER TABLE %(table)s
            ADD CONSTRAINT %(fkeyname)s
            FOREIGN KEY (%(col_name)s)
            REFERENCES revision (id)
            ''' % {'table':table_name, 'fkeyname':constraint_name,
                    'col_name':constraint_columns.keys()[0] }
        migrate_engine.execute(oursql)

    # 4 create uuids for revisions and in related tables
    revision_table = Table('revision', metadata, autoload=True)
    from sqlalchemy.sql import select
    for row in migrate_engine.execute(select([revision_table])):
        update = revision_table.update().where(revision_table.c.id==row.id).values(id=make_uuid())
        migrate_engine.execute(update)

def downgrade(migrate_engine):
    raise NotImplementedError()
