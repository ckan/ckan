"""
   This module defines standalone schema constraint classes.
"""
from sqlalchemy import schema

from migrate.exceptions import *

class ConstraintChangeset(object):
    """Base class for Constraint classes."""

    def _normalize_columns(self, cols, table_name=False):
        """Given: column objects or names; return col names and
        (maybe) a table"""
        colnames = []
        table = None
        for col in cols:
            if isinstance(col, schema.Column):
                if col.table is not None and table is None:
                    table = col.table
                if table_name:
                    col = '.'.join((col.table.name, col.name))
                else:
                    col = col.name
            colnames.append(col)
        return colnames, table

    def __do_imports(self, visitor_name, *a, **kw):
        engine = kw.pop('engine', self.table.bind)
        from migrate.changeset.databases.visitor import (get_engine_visitor,
                                                         run_single_visitor)
        visitorcallable = get_engine_visitor(engine, visitor_name)
        run_single_visitor(engine, visitorcallable, self, *a, **kw)

    def create(self, *a, **kw):
        """Create the constraint in the database.

        :param engine: the database engine to use. If this is \
        :keyword:`None` the instance's engine will be used
        :type engine: :class:`sqlalchemy.engine.base.Engine`
        :param connection: reuse connection istead of creating new one.
        :type connection: :class:`sqlalchemy.engine.base.Connection` instance
        """
        # TODO: set the parent here instead of in __init__
        self.__do_imports('constraintgenerator', *a, **kw)

    def drop(self, *a, **kw):
        """Drop the constraint from the database.

        :param engine: the database engine to use. If this is
          :keyword:`None` the instance's engine will be used
        :param cascade: Issue CASCADE drop if database supports it
        :type engine: :class:`sqlalchemy.engine.base.Engine`
        :type cascade: bool
        :param connection: reuse connection istead of creating new one.
        :type connection: :class:`sqlalchemy.engine.base.Connection` instance
        :returns: Instance with cleared columns
        """
        self.cascade = kw.pop('cascade', False)
        self.__do_imports('constraintdropper', *a, **kw)
        # the spirit of Constraint objects is that they
        # are immutable (just like in a DB.  they're only ADDed
        # or DROPped).
        #self.columns.clear()
        return self


class PrimaryKeyConstraint(ConstraintChangeset, schema.PrimaryKeyConstraint):
    """Construct PrimaryKeyConstraint

    Migrate's additional parameters:

    :param cols: Columns in constraint.
    :param table: If columns are passed as strings, this kw is required
    :type table: Table instance
    :type cols: strings or Column instances
    """

    __migrate_visit_name__ = 'migrate_primary_key_constraint'

    def __init__(self, *cols, **kwargs):
        colnames, table = self._normalize_columns(cols)
        table = kwargs.pop('table', table)
        super(PrimaryKeyConstraint, self).__init__(*colnames, **kwargs)
        if table is not None:
            self._set_parent(table)


    def autoname(self):
        """Mimic the database's automatic constraint names"""
        return "%s_pkey" % self.table.name


class ForeignKeyConstraint(ConstraintChangeset, schema.ForeignKeyConstraint):
    """Construct ForeignKeyConstraint

    Migrate's additional parameters:

    :param columns: Columns in constraint
    :param refcolumns: Columns that this FK reffers to in another table.
    :param table: If columns are passed as strings, this kw is required
    :type table: Table instance
    :type columns: list of strings or Column instances
    :type refcolumns: list of strings or Column instances
    """

    __migrate_visit_name__ = 'migrate_foreign_key_constraint'

    def __init__(self, columns, refcolumns, *args, **kwargs):
        colnames, table = self._normalize_columns(columns)
        table = kwargs.pop('table', table)
        refcolnames, reftable = self._normalize_columns(refcolumns,
                                                        table_name=True)
        super(ForeignKeyConstraint, self).__init__(colnames, refcolnames, *args,
                                                   **kwargs)
        if table is not None:
            self._set_parent(table)

    @property
    def referenced(self):
        return [e.column for e in self.elements]

    @property
    def reftable(self):
        return self.referenced[0].table

    def autoname(self):
        """Mimic the database's automatic constraint names"""
        if hasattr(self.columns, 'keys'):
            # SA <= 0.5
            firstcol = self.columns[self.columns.keys()[0]]
            ret = "%(table)s_%(firstcolumn)s_fkey" % dict(
                table=firstcol.table.name,
                firstcolumn=firstcol.name,)
        else:
            # SA >= 0.6
            ret = "%(table)s_%(firstcolumn)s_fkey" % dict(
                table=self.table.name,
                firstcolumn=self.columns[0],)
        return ret


class CheckConstraint(ConstraintChangeset, schema.CheckConstraint):
    """Construct CheckConstraint

    Migrate's additional parameters:

    :param sqltext: Plain SQL text to check condition
    :param columns: If not name is applied, you must supply this kw\
    to autoname constraint
    :param table: If columns are passed as strings, this kw is required
    :type table: Table instance
    :type columns: list of Columns instances
    :type sqltext: string
    """

    __migrate_visit_name__ = 'migrate_check_constraint'

    def __init__(self, sqltext, *args, **kwargs):
        cols = kwargs.pop('columns', [])
        if not cols and not kwargs.get('name', False):
            raise InvalidConstraintError('You must either set "name"'
                'parameter or "columns" to autogenarate it.')
        colnames, table = self._normalize_columns(cols)
        table = kwargs.pop('table', table)
        schema.CheckConstraint.__init__(self, sqltext, *args, **kwargs)
        if table is not None:
            self._set_parent(table)
        self.colnames = colnames

    def autoname(self):
        return "%(table)s_%(cols)s_check" % \
            dict(table=self.table.name, cols="_".join(self.colnames))


class UniqueConstraint(ConstraintChangeset, schema.UniqueConstraint):
    """Construct UniqueConstraint

    Migrate's additional parameters:

    :param cols: Columns in constraint.
    :param table: If columns are passed as strings, this kw is required
    :type table: Table instance
    :type cols: strings or Column instances

    .. versionadded:: 0.6.0
    """

    __migrate_visit_name__ = 'migrate_unique_constraint'

    def __init__(self, *cols, **kwargs):
        self.colnames, table = self._normalize_columns(cols)
        table = kwargs.pop('table', table)
        super(UniqueConstraint, self).__init__(*self.colnames, **kwargs)
        if table is not None:
            self._set_parent(table)

    def autoname(self):
        """Mimic the database's automatic constraint names"""
        return "%s_%s_key" % (self.table.name, self.colnames[0])
