"""
   Schema differencing support.
"""

import logging
import sqlalchemy

from sqlalchemy.types import Float

log = logging.getLogger(__name__)

def getDiffOfModelAgainstDatabase(metadata, engine, excludeTables=None):
    """
    Return differences of model against database.

    :return: object which will evaluate to :keyword:`True` if there \
      are differences else :keyword:`False`.
    """
    db_metadata = sqlalchemy.MetaData(engine)
    db_metadata.reflect()

    # sqlite will include a dynamically generated 'sqlite_sequence' table if
    # there are autoincrement sequences in the database; this should not be
    # compared.
    if engine.dialect.name == 'sqlite':
        if 'sqlite_sequence' in db_metadata.tables:
            db_metadata.remove(db_metadata.tables['sqlite_sequence'])

    return SchemaDiff(metadata, db_metadata,
                      labelA='model',
                      labelB='database',
                      excludeTables=excludeTables)


def getDiffOfModelAgainstModel(metadataA, metadataB, excludeTables=None):
    """
    Return differences of model against another model.

    :return: object which will evaluate to :keyword:`True` if there \
      are differences else :keyword:`False`.
    """
    return SchemaDiff(metadataA, metadataB, excludeTables=excludeTables)


class ColDiff(object):
    """
    Container for differences in one :class:`~sqlalchemy.schema.Column`
    between two :class:`~sqlalchemy.schema.Table` instances, ``A``
    and ``B``.

    .. attribute:: col_A

      The :class:`~sqlalchemy.schema.Column` object for A.

    .. attribute:: col_B

      The :class:`~sqlalchemy.schema.Column` object for B.

    .. attribute:: type_A

      The most generic type of the :class:`~sqlalchemy.schema.Column`
      object in A.

    .. attribute:: type_B

      The most generic type of the :class:`~sqlalchemy.schema.Column`
      object in A.

    """

    diff = False

    def __init__(self,col_A,col_B):
        self.col_A = col_A
        self.col_B = col_B

        self.type_A = col_A.type
        self.type_B = col_B.type

        self.affinity_A = self.type_A._type_affinity
        self.affinity_B = self.type_B._type_affinity

        if self.affinity_A is not self.affinity_B:
            self.diff = True
            return

        if isinstance(self.type_A,Float) or isinstance(self.type_B,Float):
            if not (isinstance(self.type_A,Float) and isinstance(self.type_B,Float)):
                self.diff=True
                return

        for attr in ('precision','scale','length'):
            A = getattr(self.type_A,attr,None)
            B = getattr(self.type_B,attr,None)
            if not (A is None or B is None) and A!=B:
                self.diff=True
                return

    def __nonzero__(self):
        return self.diff

    __bool__ = __nonzero__


class TableDiff(object):
    """
    Container for differences in one :class:`~sqlalchemy.schema.Table`
    between two :class:`~sqlalchemy.schema.MetaData` instances, ``A``
    and ``B``.

    .. attribute:: columns_missing_from_A

      A sequence of column names that were found in B but weren't in
      A.

    .. attribute:: columns_missing_from_B

      A sequence of column names that were found in A but weren't in
      B.

    .. attribute:: columns_different

      A dictionary containing information about columns that were
      found to be different.
      It maps column names to a :class:`ColDiff` objects describing the
      differences found.
    """
    __slots__ = (
        'columns_missing_from_A',
        'columns_missing_from_B',
        'columns_different',
        )

    def __nonzero__(self):
        return bool(
            self.columns_missing_from_A or
            self.columns_missing_from_B or
            self.columns_different
            )

    __bool__ = __nonzero__

class SchemaDiff(object):
    """
    Compute the difference between two :class:`~sqlalchemy.schema.MetaData`
    objects.

    The string representation of a :class:`SchemaDiff` will summarise
    the changes found between the two
    :class:`~sqlalchemy.schema.MetaData` objects.

    The length of a :class:`SchemaDiff` will give the number of
    changes found, enabling it to be used much like a boolean in
    expressions.

    :param metadataA:
      First :class:`~sqlalchemy.schema.MetaData` to compare.

    :param metadataB:
      Second :class:`~sqlalchemy.schema.MetaData` to compare.

    :param labelA:
      The label to use in messages about the first
      :class:`~sqlalchemy.schema.MetaData`.

    :param labelB:
      The label to use in messages about the second
      :class:`~sqlalchemy.schema.MetaData`.

    :param excludeTables:
      A sequence of table names to exclude.

    .. attribute:: tables_missing_from_A

      A sequence of table names that were found in B but weren't in
      A.

    .. attribute:: tables_missing_from_B

      A sequence of table names that were found in A but weren't in
      B.

    .. attribute:: tables_different

      A dictionary containing information about tables that were found
      to be different.
      It maps table names to a :class:`TableDiff` objects describing the
      differences found.
    """

    def __init__(self,
                 metadataA, metadataB,
                 labelA='metadataA',
                 labelB='metadataB',
                 excludeTables=None):

        self.metadataA, self.metadataB = metadataA, metadataB
        self.labelA, self.labelB = labelA, labelB
        self.label_width = max(len(labelA),len(labelB))
        excludeTables = set(excludeTables or [])

        A_table_names = set(metadataA.tables.keys())
        B_table_names = set(metadataB.tables.keys())

        self.tables_missing_from_A = sorted(
            B_table_names - A_table_names - excludeTables
            )
        self.tables_missing_from_B = sorted(
            A_table_names - B_table_names - excludeTables
            )

        self.tables_different = {}
        for table_name in A_table_names.intersection(B_table_names):

            td = TableDiff()

            A_table = metadataA.tables[table_name]
            B_table = metadataB.tables[table_name]

            A_column_names = set(A_table.columns.keys())
            B_column_names = set(B_table.columns.keys())

            td.columns_missing_from_A = sorted(
                B_column_names - A_column_names
                )

            td.columns_missing_from_B = sorted(
                A_column_names - B_column_names
                )

            td.columns_different = {}

            for col_name in A_column_names.intersection(B_column_names):

                cd = ColDiff(
                    A_table.columns.get(col_name),
                    B_table.columns.get(col_name)
                    )

                if cd:
                    td.columns_different[col_name]=cd

            # XXX - index and constraint differences should
            #       be checked for here

            if td:
                self.tables_different[table_name]=td

    def __str__(self):
        ''' Summarize differences. '''
        out = []
        column_template ='      %%%is: %%r' % self.label_width

        for names,label in (
            (self.tables_missing_from_A,self.labelA),
            (self.tables_missing_from_B,self.labelB),
            ):
            if names:
                out.append(
                    '  tables missing from %s: %s' % (
                        label,', '.join(sorted(names))
                        )
                    )

        for name,td in sorted(self.tables_different.items()):
            out.append(
               '  table with differences: %s' % name
               )
            for names,label in (
                (td.columns_missing_from_A,self.labelA),
                (td.columns_missing_from_B,self.labelB),
                ):
                if names:
                    out.append(
                        '    %s missing these columns: %s' % (
                            label,', '.join(sorted(names))
                            )
                        )
            for name,cd in td.columns_different.items():
                out.append('    column with differences: %s' % name)
                out.append(column_template % (self.labelA,cd.col_A))
                out.append(column_template % (self.labelB,cd.col_B))

        if out:
            out.insert(0, 'Schema diffs:')
            return '\n'.join(out)
        else:
            return 'No schema diffs'

    def __len__(self):
        """
        Used in bool evaluation, return of 0 means no diffs.
        """
        return (
            len(self.tables_missing_from_A) +
            len(self.tables_missing_from_B) +
            len(self.tables_different)
            )
