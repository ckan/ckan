"""
   MySQL database specific implementations of changeset classes.
"""

import sqlalchemy
from sqlalchemy.databases import mysql as sa_base
from sqlalchemy import types as sqltypes

from migrate import exceptions
from migrate.changeset import ansisql
from migrate.changeset import util



MySQLSchemaGenerator = sa_base.MySQLDDLCompiler

class MySQLColumnGenerator(MySQLSchemaGenerator, ansisql.ANSIColumnGenerator):
    pass


class MySQLColumnDropper(ansisql.ANSIColumnDropper):
    pass


class MySQLSchemaChanger(MySQLSchemaGenerator, ansisql.ANSISchemaChanger):

    def visit_column(self, delta):
        table = delta.table
        colspec = self.get_column_specification(delta.result_column)
        if delta.result_column.autoincrement:
            primary_keys = [c for c in table.primary_key.columns
                       if (c.autoincrement and
                            isinstance(c.type, sqltypes.Integer) and
                            not c.foreign_keys)]

            if primary_keys:
                first = primary_keys.pop(0)
                if first.name == delta.current_name:
                    colspec += " AUTO_INCREMENT"
        q = util.safe_quote(table)
        old_col_name = self.preparer.quote(delta.current_name, q)

        self.start_alter_table(table)

        self.append("CHANGE COLUMN %s " % old_col_name)
        self.append(colspec)
        self.execute()

    def visit_index(self, param):
        # If MySQL can do this, I can't find how
        raise exceptions.NotSupportedError("MySQL cannot rename indexes")


class MySQLConstraintGenerator(ansisql.ANSIConstraintGenerator):
    pass


class MySQLConstraintDropper(MySQLSchemaGenerator, ansisql.ANSIConstraintDropper):
    def visit_migrate_check_constraint(self, *p, **k):
        raise exceptions.NotSupportedError("MySQL does not support CHECK"
            " constraints, use triggers instead.")


class MySQLDialect(ansisql.ANSIDialect):
    columngenerator = MySQLColumnGenerator
    columndropper = MySQLColumnDropper
    schemachanger = MySQLSchemaChanger
    constraintgenerator = MySQLConstraintGenerator
    constraintdropper = MySQLConstraintDropper
