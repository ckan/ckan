"""
   Extensions to SQLAlchemy for altering existing tables.

   At the moment, this isn't so much based off of ANSI as much as
   things that just happen to work with multiple databases.
"""

import sqlalchemy as sa
from sqlalchemy.schema import SchemaVisitor
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.sql import ClauseElement
from sqlalchemy.schema import (ForeignKeyConstraint,
                               PrimaryKeyConstraint,
                               CheckConstraint,
                               UniqueConstraint,
                               Index)

from migrate import exceptions
import sqlalchemy.sql.compiler
from migrate.changeset import constraint
from migrate.changeset import util
from six.moves import StringIO

from sqlalchemy.schema import AddConstraint, DropConstraint
from sqlalchemy.sql.compiler import DDLCompiler
SchemaGenerator = SchemaDropper = DDLCompiler


class AlterTableVisitor(SchemaVisitor):
    """Common operations for ``ALTER TABLE`` statements."""

    # engine.Compiler looks for .statement
    # when it spawns off a new compiler
    statement = ClauseElement()

    def append(self, s):
        """Append content to the SchemaIterator's query buffer."""

        self.buffer.write(s)

    def execute(self):
        """Execute the contents of the SchemaIterator's buffer."""
        try:
            return self.connection.execute(self.buffer.getvalue())
        finally:
            self.buffer.seek(0)
            self.buffer.truncate()

    def __init__(self, dialect, connection, **kw):
        self.connection = connection
        self.buffer = StringIO()
        self.preparer = dialect.identifier_preparer
        self.dialect = dialect

    def traverse_single(self, elem):
        ret = super(AlterTableVisitor, self).traverse_single(elem)
        if ret:
            # adapt to 0.6 which uses a string-returning
            # object
            self.append(" %s" % ret)

    def _to_table(self, param):
        """Returns the table object for the given param object."""
        if isinstance(param, (sa.Column, sa.Index, sa.schema.Constraint)):
            ret = param.table
        else:
            ret = param
        return ret

    def start_alter_table(self, param):
        """Returns the start of an ``ALTER TABLE`` SQL-Statement.

        Use the param object to determine the table name and use it
        for building the SQL statement.

        :param param: object to determine the table from
        :type param: :class:`sqlalchemy.Column`, :class:`sqlalchemy.Index`,
          :class:`sqlalchemy.schema.Constraint`, :class:`sqlalchemy.Table`,
          or string (table name)
        """
        table = self._to_table(param)
        self.append('\nALTER TABLE %s ' % self.preparer.format_table(table))
        return table


class ANSIColumnGenerator(AlterTableVisitor, SchemaGenerator):
    """Extends ansisql generator for column creation (alter table add col)"""

    def visit_column(self, column):
        """Create a column (table already exists).

        :param column: column object
        :type column: :class:`sqlalchemy.Column` instance
        """
        if column.default is not None:
            self.traverse_single(column.default)

        table = self.start_alter_table(column)
        self.append("ADD ")
        self.append(self.get_column_specification(column))

        for cons in column.constraints:
            self.traverse_single(cons)
        self.execute()

        # ALTER TABLE STATEMENTS

        # add indexes and unique constraints
        if column.index_name:
            Index(column.index_name,column).create()
        elif column.unique_name:
            constraint.UniqueConstraint(column,
                                        name=column.unique_name).create()

        # SA bounds FK constraints to table, add manually
        for fk in column.foreign_keys:
            self.add_foreignkey(fk.constraint)

        # add primary key constraint if needed
        if column.primary_key_name:
            cons = constraint.PrimaryKeyConstraint(column,
                                                   name=column.primary_key_name)
            cons.create()

    def add_foreignkey(self, fk):
        self.connection.execute(AddConstraint(fk))

class ANSIColumnDropper(AlterTableVisitor, SchemaDropper):
    """Extends ANSI SQL dropper for column dropping (``ALTER TABLE
    DROP COLUMN``).
    """

    def visit_column(self, column):
        """Drop a column from its table.

        :param column: the column object
        :type column: :class:`sqlalchemy.Column`
        """
        table = self.start_alter_table(column)
        self.append('DROP COLUMN %s' % self.preparer.format_column(column))
        self.execute()


class ANSISchemaChanger(AlterTableVisitor, SchemaGenerator):
    """Manages changes to existing schema elements.

    Note that columns are schema elements; ``ALTER TABLE ADD COLUMN``
    is in SchemaGenerator.

    All items may be renamed. Columns can also have many of their properties -
    type, for example - changed.

    Each function is passed a tuple, containing (object, name); where
    object is a type of object you'd expect for that function
    (ie. table for visit_table) and name is the object's new
    name. NONE means the name is unchanged.
    """

    def visit_table(self, table):
        """Rename a table. Other ops aren't supported."""
        self.start_alter_table(table)
        q = util.safe_quote(table)
        self.append("RENAME TO %s" % self.preparer.quote(table.new_name, q))
        self.execute()

    def visit_index(self, index):
        """Rename an index"""
        if hasattr(self, '_validate_identifier'):
            # SA <= 0.6.3
            self.append("ALTER INDEX %s RENAME TO %s" % (
                    self.preparer.quote(
                        self._validate_identifier(
                            index.name, True), index.quote),
                    self.preparer.quote(
                        self._validate_identifier(
                            index.new_name, True), index.quote)))
        elif hasattr(self, '_index_identifier'):
            # SA >= 0.6.5, < 0.8
            self.append("ALTER INDEX %s RENAME TO %s" % (
                    self.preparer.quote(
                        self._index_identifier(
                            index.name), index.quote),
                    self.preparer.quote(
                        self._index_identifier(
                            index.new_name), index.quote)))
        else:
            # SA >= 0.8
            class NewName(object):
                """Map obj.name -> obj.new_name"""
                def __init__(self, index):
                    self.name = index.new_name
                    self._obj = index

                def __getattr__(self, attr):
                    if attr == 'name':
                        return getattr(self, attr)
                    return getattr(self._obj, attr)

            self.append("ALTER INDEX %s RENAME TO %s" % (
                    self._prepared_index_name(index),
                    self._prepared_index_name(NewName(index))))

        self.execute()

    def visit_column(self, delta):
        """Rename/change a column."""
        # ALTER COLUMN is implemented as several ALTER statements
        keys = delta.keys()
        if 'type' in keys:
            self._run_subvisit(delta, self._visit_column_type)
        if 'nullable' in keys:
            self._run_subvisit(delta, self._visit_column_nullable)
        if 'server_default' in keys:
            # Skip 'default': only handle server-side defaults, others
            # are managed by the app, not the db.
            self._run_subvisit(delta, self._visit_column_default)
        if 'name' in keys:
            self._run_subvisit(delta, self._visit_column_name, start_alter=False)

    def _run_subvisit(self, delta, func, start_alter=True):
        """Runs visit method based on what needs to be changed on column"""
        table = self._to_table(delta.table)
        col_name = delta.current_name
        if start_alter:
            self.start_alter_column(table, col_name)
        ret = func(table, delta.result_column, delta)
        self.execute()

    def start_alter_column(self, table, col_name):
        """Starts ALTER COLUMN"""
        self.start_alter_table(table)
        q = util.safe_quote(table)
        self.append("ALTER COLUMN %s " % self.preparer.quote(col_name, q))

    def _visit_column_nullable(self, table, column, delta):
        nullable = delta['nullable']
        if nullable:
            self.append("DROP NOT NULL")
        else:
            self.append("SET NOT NULL")

    def _visit_column_default(self, table, column, delta):
        default_text = self.get_column_default_string(column)
        if default_text is not None:
            self.append("SET DEFAULT %s" % default_text)
        else:
            self.append("DROP DEFAULT")

    def _visit_column_type(self, table, column, delta):
        type_ = delta['type']
        type_text = str(type_.compile(dialect=self.dialect))
        self.append("TYPE %s" % type_text)

    def _visit_column_name(self, table, column, delta):
        self.start_alter_table(table)
        q = util.safe_quote(table)
        col_name = self.preparer.quote(delta.current_name, q)
        new_name = self.preparer.format_column(delta.result_column)
        self.append('RENAME COLUMN %s TO %s' % (col_name, new_name))


class ANSIConstraintCommon(AlterTableVisitor):
    """
    Migrate's constraints require a separate creation function from
    SA's: Migrate's constraints are created independently of a table;
    SA's are created at the same time as the table.
    """

    def get_constraint_name(self, cons):
        """Gets a name for the given constraint.

        If the name is already set it will be used otherwise the
        constraint's :meth:`autoname <migrate.changeset.constraint.ConstraintChangeset.autoname>`
        method is used.

        :param cons: constraint object
        """
        if cons.name is not None:
            ret = cons.name
        else:
            ret = cons.name = cons.autoname()
        return ret

    def visit_migrate_primary_key_constraint(self, *p, **k):
        self._visit_constraint(*p, **k)

    def visit_migrate_foreign_key_constraint(self, *p, **k):
        self._visit_constraint(*p, **k)

    def visit_migrate_check_constraint(self, *p, **k):
        self._visit_constraint(*p, **k)

    def visit_migrate_unique_constraint(self, *p, **k):
        self._visit_constraint(*p, **k)

class ANSIConstraintGenerator(ANSIConstraintCommon, SchemaGenerator):
    def _visit_constraint(self, constraint):
        constraint.name = self.get_constraint_name(constraint)
        self.append(self.process(AddConstraint(constraint)))
        self.execute()

class ANSIConstraintDropper(ANSIConstraintCommon, SchemaDropper):
    def _visit_constraint(self, constraint):
        constraint.name = self.get_constraint_name(constraint)
        self.append(self.process(DropConstraint(constraint, cascade=constraint.cascade)))
        self.execute()


class ANSIDialect(DefaultDialect):
    columngenerator = ANSIColumnGenerator
    columndropper = ANSIColumnDropper
    schemachanger = ANSISchemaChanger
    constraintgenerator = ANSIConstraintGenerator
    constraintdropper = ANSIConstraintDropper
