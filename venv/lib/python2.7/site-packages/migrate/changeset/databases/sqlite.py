"""
   `SQLite`_ database specific implementations of changeset classes.

   .. _`SQLite`: http://www.sqlite.org/
"""
try:  # Python 3
    from collections import MutableMapping as DictMixin
except ImportError:  # Python 2
    from UserDict import DictMixin
from copy import copy
import re

from sqlalchemy.databases import sqlite as sa_base
from sqlalchemy.schema import ForeignKeyConstraint
from sqlalchemy.schema import UniqueConstraint

from migrate import exceptions
from migrate.changeset import ansisql


SQLiteSchemaGenerator = sa_base.SQLiteDDLCompiler


class SQLiteCommon(object):

    def _not_supported(self, op):
        raise exceptions.NotSupportedError("SQLite does not support "
            "%s; see http://www.sqlite.org/lang_altertable.html" % op)


class SQLiteHelper(SQLiteCommon):

    def _filter_columns(self, cols, table):
        """Splits the string of columns and returns those only in the table.

        :param cols: comma-delimited string of table columns
        :param table: the table to check
        :return: list of columns in the table
        """
        columns = []
        for c in cols.split(","):
            if c in table.columns:
                # There was a bug in reflection of SQLite columns with
                # reserved identifiers as names (SQLite can return them
                # wrapped with double quotes), so strip double quotes.
                columns.extend(c.strip(' "'))
        return columns

    def _get_constraints(self, table):
        """Retrieve information about existing constraints of the table

        This feature is needed for recreate_table() to work properly.
        """

        data = table.metadata.bind.execute(
            """SELECT sql
               FROM sqlite_master
               WHERE
                   type='table' AND
                   name=:table_name""",
            table_name=table.name
        ).fetchone()[0]

        UNIQUE_PATTERN = "CONSTRAINT (\w+) UNIQUE \(([^\)]+)\)"
        constraints = []
        for name, cols in re.findall(UNIQUE_PATTERN, data):
            # Filter out any columns that were dropped from the table.
            columns = self._filter_columns(cols, table)
            if columns:
                constraints.extend(UniqueConstraint(*columns, name=name))

        FKEY_PATTERN = "CONSTRAINT (\w+) FOREIGN KEY \(([^\)]+)\)"
        for name, cols in re.findall(FKEY_PATTERN, data):
            # Filter out any columns that were dropped from the table.
            columns = self._filter_columns(cols, table)
            if columns:
                constraints.extend(ForeignKeyConstraint(*columns, name=name))

        return constraints

    def recreate_table(self, table, column=None, delta=None,
                       omit_constraints=None):
        table_name = self.preparer.format_table(table)

        # we remove all indexes so as not to have
        # problems during copy and re-create
        for index in table.indexes:
            index.drop()

        # reflect existing constraints
        for constraint in self._get_constraints(table):
            table.append_constraint(constraint)
        # omit given constraints when creating a new table if required
        table.constraints = set([
            cons for cons in table.constraints
            if omit_constraints is None or cons.name not in omit_constraints
        ])

        self.append('ALTER TABLE %s RENAME TO migration_tmp' % table_name)
        self.execute()

        insertion_string = self._modify_table(table, column, delta)

        table.create(bind=self.connection)
        self.append(insertion_string % {'table_name': table_name})
        self.execute()
        self.append('DROP TABLE migration_tmp')
        self.execute()

    def visit_column(self, delta):
        if isinstance(delta, DictMixin):
            column = delta.result_column
            table = self._to_table(delta.table)
        else:
            column = delta
            table = self._to_table(column.table)
        self.recreate_table(table,column,delta)

class SQLiteColumnGenerator(SQLiteSchemaGenerator,
                            ansisql.ANSIColumnGenerator,
                            # at the end so we get the normal
                            # visit_column by default
                            SQLiteHelper,
                            SQLiteCommon
                            ):
    """SQLite ColumnGenerator"""

    def _modify_table(self, table, column, delta):
        columns = ' ,'.join(map(
                self.preparer.format_column,
                [c for c in table.columns if c.name!=column.name]))
        return ('INSERT INTO %%(table_name)s (%(cols)s) '
                'SELECT %(cols)s from migration_tmp')%{'cols':columns}

    def visit_column(self,column):
        if column.foreign_keys:
            SQLiteHelper.visit_column(self,column)
        else:
            super(SQLiteColumnGenerator,self).visit_column(column)

class SQLiteColumnDropper(SQLiteHelper, ansisql.ANSIColumnDropper):
    """SQLite ColumnDropper"""

    def _modify_table(self, table, column, delta):

        columns = ' ,'.join(map(self.preparer.format_column, table.columns))
        return 'INSERT INTO %(table_name)s SELECT ' + columns + \
            ' from migration_tmp'

    def visit_column(self,column):
        # For SQLite, we *have* to remove the column here so the table
        # is re-created properly.
        column.remove_from_table(column.table,unset_table=False)
        super(SQLiteColumnDropper,self).visit_column(column)


class SQLiteSchemaChanger(SQLiteHelper, ansisql.ANSISchemaChanger):
    """SQLite SchemaChanger"""

    def _modify_table(self, table, column, delta):
        return 'INSERT INTO %(table_name)s SELECT * from migration_tmp'

    def visit_index(self, index):
        """Does not support ALTER INDEX"""
        self._not_supported('ALTER INDEX')


class SQLiteConstraintGenerator(ansisql.ANSIConstraintGenerator, SQLiteHelper, SQLiteCommon):

    def visit_migrate_primary_key_constraint(self, constraint):
        tmpl = "CREATE UNIQUE INDEX %s ON %s ( %s )"
        cols = ', '.join(map(self.preparer.format_column, constraint.columns))
        tname = self.preparer.format_table(constraint.table)
        name = self.get_constraint_name(constraint)
        msg = tmpl % (name, tname, cols)
        self.append(msg)
        self.execute()

    def _modify_table(self, table, column, delta):
        return 'INSERT INTO %(table_name)s SELECT * from migration_tmp'

    def visit_migrate_foreign_key_constraint(self, *p, **k):
        self.recreate_table(p[0].table)

    def visit_migrate_unique_constraint(self, *p, **k):
        self.recreate_table(p[0].table)


class SQLiteConstraintDropper(ansisql.ANSIColumnDropper,
                              SQLiteHelper,
                              ansisql.ANSIConstraintCommon):

    def _modify_table(self, table, column, delta):
        return 'INSERT INTO %(table_name)s SELECT * from migration_tmp'

    def visit_migrate_primary_key_constraint(self, constraint):
        tmpl = "DROP INDEX %s "
        name = self.get_constraint_name(constraint)
        msg = tmpl % (name)
        self.append(msg)
        self.execute()

    def visit_migrate_foreign_key_constraint(self, *p, **k):
        self.recreate_table(p[0].table, omit_constraints=[p[0].name])

    def visit_migrate_check_constraint(self, *p, **k):
        self._not_supported('ALTER TABLE DROP CONSTRAINT')

    def visit_migrate_unique_constraint(self, *p, **k):
        self.recreate_table(p[0].table, omit_constraints=[p[0].name])


# TODO: technically primary key is a NOT NULL + UNIQUE constraint, should add NOT NULL to index

class SQLiteDialect(ansisql.ANSIDialect):
    columngenerator = SQLiteColumnGenerator
    columndropper = SQLiteColumnDropper
    schemachanger = SQLiteSchemaChanger
    constraintgenerator = SQLiteConstraintGenerator
    constraintdropper = SQLiteConstraintDropper
