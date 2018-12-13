"""
    DB2 database specific implementations of changeset classes.
"""

import logging

from ibm_db_sa import base
from sqlalchemy.schema import (AddConstraint,
                               CreateIndex,
                               DropConstraint)
from sqlalchemy.schema import (Index,
                               PrimaryKeyConstraint,
                               UniqueConstraint)

from migrate.changeset import ansisql
from migrate.changeset import constraint
from migrate.changeset import util
from migrate import exceptions


LOG = logging.getLogger(__name__)

IBMDBSchemaGenerator = base.IBM_DBDDLCompiler


def get_server_version_info(dialect):
    """Returns the DB2 server major and minor version as a list of ints."""
    return [int(ver_token) for ver_token in dialect.dbms_ver.split('.')[0:2]]


def is_unique_constraint_with_null_columns_supported(dialect):
    """Checks to see if the DB2 version is at least 10.5.

    This is needed for checking if unique constraints with null columns
    are supported.
    """
    return get_server_version_info(dialect) >= [10, 5]


class IBMDBColumnGenerator(IBMDBSchemaGenerator,
                           ansisql.ANSIColumnGenerator):
    def visit_column(self, column):
        nullable = True
        if not column.nullable:
            nullable = False
            column.nullable = True

        table = self.start_alter_table(column)
        self.append("ADD COLUMN ")
        self.append(self.get_column_specification(column))

        for cons in column.constraints:
            self.traverse_single(cons)
        if column.default is not None:
            self.traverse_single(column.default)
        self.execute()

        #ALTER TABLE STATEMENTS
        if not nullable:
            self.start_alter_table(column)
            self.append("ALTER COLUMN %s SET NOT NULL" %
                        self.preparer.format_column(column))
            self.execute()
            self.append("CALL SYSPROC.ADMIN_CMD('REORG TABLE %s')" %
                        self.preparer.format_table(table))
            self.execute()

        # add indexes and unique constraints
        if column.index_name:
            Index(column.index_name, column).create()
        elif column.unique_name:
            constraint.UniqueConstraint(column,
                                        name=column.unique_name).create()

        # SA bounds FK constraints to table, add manually
        for fk in column.foreign_keys:
            self.add_foreignkey(fk.constraint)

        # add primary key constraint if needed
        if column.primary_key_name:
            pk = constraint.PrimaryKeyConstraint(
                column, name=column.primary_key_name)
            pk.create()

        self.append("COMMIT")
        self.execute()
        self.append("CALL SYSPROC.ADMIN_CMD('REORG TABLE %s')" %
                    self.preparer.format_table(table))
        self.execute()


class IBMDBColumnDropper(ansisql.ANSIColumnDropper):
    def visit_column(self, column):
        """Drop a column from its table.

        :param column: the column object
        :type column: :class:`sqlalchemy.Column`
        """
        #table = self.start_alter_table(column)
        super(IBMDBColumnDropper, self).visit_column(column)
        self.append("CALL SYSPROC.ADMIN_CMD('REORG TABLE %s')" %
                    self.preparer.format_table(column.table))
        self.execute()


class IBMDBSchemaChanger(IBMDBSchemaGenerator, ansisql.ANSISchemaChanger):
    def visit_table(self, table):
        """Rename a table; #38. Other ops aren't supported."""

        self._rename_table(table)
        q = util.safe_quote(table)
        self.append("TO %s" % self.preparer.quote(table.new_name, q))
        self.execute()
        self.append("COMMIT")
        self.execute()

    def _rename_table(self, table):
        self.append("RENAME TABLE %s " % self.preparer.format_table(table))

    def visit_index(self, index):
        if hasattr(self, '_index_identifier'):
            # SA >= 0.6.5, < 0.8
            old_name = self.preparer.quote(
                self._index_identifier(index.name), index.quote)
            new_name = self.preparer.quote(
                self._index_identifier(index.new_name), index.quote)
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

            old_name = self._prepared_index_name(index)
            new_name = self._prepared_index_name(NewName(index))

        self.append("RENAME INDEX %s TO %s" % (old_name, new_name))
        self.execute()
        self.append("COMMIT")
        self.execute()

    def _run_subvisit(self, delta, func, start_alter=True):
        """Runs visit method based on what needs to be changed on column"""
        table = delta.table
        q = util.safe_quote(table)
        if start_alter:
            self.start_alter_table(table)
        ret = func(table,
                   self.preparer.quote(delta.current_name, q),
                   delta)
        self.execute()
        self._reorg_table(self.preparer.format_table(delta.table))

    def _reorg_table(self, delta):
        self.append("CALL SYSPROC.ADMIN_CMD('REORG TABLE %s')" % delta)
        self.execute()

    def visit_column(self, delta):
        keys = delta.keys()
        tr = self.connection.begin()
        column = delta.result_column.copy()

        if 'type' in keys:
            try:
                self._run_subvisit(delta, self._visit_column_change, False)
            except Exception as e:
                LOG.warn("Unable to change the column type. Error: %s" % e)

            if column.primary_key and 'primary_key' not in keys:
                try:
                    self._run_subvisit(delta, self._visit_primary_key)
                except Exception as e:
                    LOG.warn("Unable to add primary key. Error: %s" % e)

        if 'nullable' in keys:
            self._run_subvisit(delta, self._visit_column_nullable)

        if 'server_default' in keys:
            self._run_subvisit(delta, self._visit_column_default)

        if 'primary_key' in keys:
            self._run_subvisit(delta, self._visit_primary_key)
            self._run_subvisit(delta, self._visit_unique_constraint)

        if 'name' in keys:
            try:
                self._run_subvisit(delta, self._visit_column_name, False)
            except Exception as e:
                LOG.warn("Unable to change column %(name)s. Error: %(error)s" %
                         {'name': delta.current_name, 'error': e})

        self._reorg_table(self.preparer.format_table(delta.table))
        self.append("COMMIT")
        self.execute()
        tr.commit()

    def _visit_unique_constraint(self, table, col_name, delta):
        # Add primary key to the current column
        self.append("ADD CONSTRAINT %s " % col_name)
        self.append("UNIQUE (%s)" % col_name)

    def _visit_primary_key(self, table, col_name, delta):
        # Add primary key to the current column
        self.append("ADD PRIMARY KEY (%s)" % col_name)

    def _visit_column_name(self, table, col_name, delta):
        column = delta.result_column.copy()

        # Delete the primary key before renaming the column
        if column.primary_key:
            try:
                self.start_alter_table(table)
                self.append("DROP PRIMARY KEY")
                self.execute()
            except Exception:
                LOG.debug("Continue since Primary key does not exist.")

        self.start_alter_table(table)
        new_name = self.preparer.format_column(delta.result_column)
        self.append("RENAME COLUMN %s TO %s" % (col_name, new_name))

        if column.primary_key:
            # execute the rename before adding primary key back
            self.execute()
            self.start_alter_table(table)
            self.append("ADD PRIMARY KEY (%s)" % new_name)

    def _visit_column_nullable(self, table, col_name, delta):
        self.append("ALTER COLUMN %s " % col_name)
        nullable = delta['nullable']
        if nullable:
            self.append("DROP NOT NULL")
        else:
            self.append("SET NOT NULL")

    def _visit_column_default(self, table, col_name, delta):
        default_text = self.get_column_default_string(delta.result_column)
        self.append("ALTER COLUMN %s " % col_name)
        if default_text is None:
            self.append("DROP DEFAULT")
        else:
            self.append("SET WITH DEFAULT %s" % default_text)

    def _visit_column_change(self, table, col_name, delta):
        column = delta.result_column.copy()

        # Delete the primary key before
        if column.primary_key:
            try:
                self.start_alter_table(table)
                self.append("DROP PRIMARY KEY")
                self.execute()
            except Exception:
                LOG.debug("Continue since Primary key does not exist.")
            # Delete the identity before
            try:
                self.start_alter_table(table)
                self.append("ALTER COLUMN %s DROP IDENTITY" % col_name)
                self.execute()
            except Exception:
                LOG.debug("Continue since identity does not exist.")

        column.default = None
        if not column.table:
            column.table = delta.table
        self.start_alter_table(table)
        self.append("ALTER COLUMN %s " % col_name)
        self.append("SET DATA TYPE ")
        type_text = self.dialect.type_compiler.process(
            delta.result_column.type)
        self.append(type_text)


class IBMDBConstraintGenerator(ansisql.ANSIConstraintGenerator):
    def _visit_constraint(self, constraint):
        constraint.name = self.get_constraint_name(constraint)
        if (isinstance(constraint, UniqueConstraint) and
                is_unique_constraint_with_null_columns_supported(
                    self.dialect)):
            for column in constraint:
                if column.nullable:
                    constraint.exclude_nulls = True
                    break
        if getattr(constraint, 'exclude_nulls', None):
            index = Index(constraint.name,
                          *(column for column in constraint),
                          unique=True)
            sql = self.process(CreateIndex(index))
            sql += ' EXCLUDE NULL KEYS'
        else:
            sql = self.process(AddConstraint(constraint))
        self.append(sql)
        self.execute()


class IBMDBConstraintDropper(ansisql.ANSIConstraintDropper,
                             ansisql.ANSIConstraintCommon):
    def _visit_constraint(self, constraint):
        constraint.name = self.get_constraint_name(constraint)
        if (isinstance(constraint, UniqueConstraint) and
                is_unique_constraint_with_null_columns_supported(
                    self.dialect)):
            for column in constraint:
                if column.nullable:
                    constraint.exclude_nulls = True
                    break
        if getattr(constraint, 'exclude_nulls', None):
            if hasattr(self, '_index_identifier'):
                # SA >= 0.6.5, < 0.8
                index_name = self.preparer.quote(
                    self._index_identifier(constraint.name),
                    constraint.quote)
            else:
                # SA >= 0.8
                index_name = self._prepared_index_name(constraint)
            sql = 'DROP INDEX %s ' % index_name
        else:
            sql = self.process(DropConstraint(constraint,
                                              cascade=constraint.cascade))
        self.append(sql)
        self.execute()

    def visit_migrate_primary_key_constraint(self, constraint):
        self.start_alter_table(constraint.table)
        self.append("DROP PRIMARY KEY")
        self.execute()


class IBMDBDialect(ansisql.ANSIDialect):
    columngenerator = IBMDBColumnGenerator
    columndropper = IBMDBColumnDropper
    schemachanger = IBMDBSchemaChanger
    constraintgenerator = IBMDBConstraintGenerator
    constraintdropper = IBMDBConstraintDropper
