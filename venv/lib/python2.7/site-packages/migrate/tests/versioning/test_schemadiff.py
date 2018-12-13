# -*- coding: utf-8 -*-

import os

from sqlalchemy import *

from migrate.versioning import schemadiff

from migrate.tests import fixture

class SchemaDiffBase(fixture.DB):

    level = fixture.DB.CONNECT
    def _make_table(self,*cols,**kw):
        self.table = Table('xtable', self.meta,
            Column('id',Integer(), primary_key=True),
            *cols
        )
        if kw.get('create',True):
            self.table.create()

    def _assert_diff(self,col_A,col_B):
        self._make_table(col_A)
        self.meta.clear()
        self._make_table(col_B,create=False)
        diff = self._run_diff()
        # print diff
        self.assertTrue(diff)
        self.assertEqual(1,len(diff.tables_different))
        td = list(diff.tables_different.values())[0]
        self.assertEqual(1,len(td.columns_different))
        cd = list(td.columns_different.values())[0]
        label_width = max(len(self.name1), len(self.name2))
        self.assertEqual(('Schema diffs:\n'
             '  table with differences: xtable\n'
             '    column with differences: data\n'
             '      %*s: %r\n'
             '      %*s: %r')%(
                label_width,
                self.name1,
                cd.col_A,
                label_width,
                self.name2,
                cd.col_B
                ),str(diff))

class Test_getDiffOfModelAgainstDatabase(SchemaDiffBase):
    name1 = 'model'
    name2 = 'database'

    def _run_diff(self,**kw):
        return schemadiff.getDiffOfModelAgainstDatabase(
            self.meta, self.engine, **kw
            )

    @fixture.usedb()
    def test_table_missing_in_db(self):
        self._make_table(create=False)
        diff = self._run_diff()
        self.assertTrue(diff)
        self.assertEqual('Schema diffs:\n  tables missing from %s: xtable' % self.name2,
            str(diff))

    @fixture.usedb()
    def test_table_missing_in_model(self):
        self._make_table()
        self.meta.clear()
        diff = self._run_diff()
        self.assertTrue(diff)
        self.assertEqual('Schema diffs:\n  tables missing from %s: xtable' % self.name1,
            str(diff))

    @fixture.usedb()
    def test_column_missing_in_db(self):
        # db
        Table('xtable', self.meta,
              Column('id',Integer(), primary_key=True),
              ).create()
        self.meta.clear()
        # model
        self._make_table(
            Column('xcol',Integer()),
            create=False
            )
        # run diff
        diff = self._run_diff()
        self.assertTrue(diff)
        self.assertEqual('Schema diffs:\n'
            '  table with differences: xtable\n'
            '    %s missing these columns: xcol' % self.name2,
            str(diff))

    @fixture.usedb()
    def test_column_missing_in_model(self):
        # db
        self._make_table(
            Column('xcol',Integer()),
            )
        self.meta.clear()
        # model
        self._make_table(
            create=False
            )
        # run diff
        diff = self._run_diff()
        self.assertTrue(diff)
        self.assertEqual('Schema diffs:\n'
            '  table with differences: xtable\n'
            '    %s missing these columns: xcol' % self.name1,
            str(diff))

    @fixture.usedb()
    def test_exclude_tables(self):
        # db
        Table('ytable', self.meta,
              Column('id',Integer(), primary_key=True),
              ).create()
        Table('ztable', self.meta,
              Column('id',Integer(), primary_key=True),
              ).create()
        self.meta.clear()
        # model
        self._make_table(
            create=False
            )
        Table('ztable', self.meta,
              Column('id',Integer(), primary_key=True),
              )
        # run diff
        diff = self._run_diff(excludeTables=('xtable','ytable'))
        # ytable only in database
        # xtable only in model
        # ztable identical on both
        # ...so we expect no diff!
        self.assertFalse(diff)
        self.assertEqual('No schema diffs',str(diff))

    @fixture.usedb()
    def test_identical_just_pk(self):
        self._make_table()
        diff = self._run_diff()
        self.assertFalse(diff)
        self.assertEqual('No schema diffs',str(diff))


    @fixture.usedb()
    def test_different_type(self):
        self._assert_diff(
            Column('data', String(10)),
            Column('data', Integer()),
            )

    @fixture.usedb()
    def test_int_vs_float(self):
        self._assert_diff(
            Column('data', Integer()),
            Column('data', Float()),
            )

    # NOTE(mriedem): The ibm_db_sa driver handles the Float() as a DOUBLE()
    # which extends Numeric() but isn't defined in sqlalchemy.types, so we
    # can't check for it as a special case like is done in schemadiff.ColDiff.
    @fixture.usedb(not_supported='ibm_db_sa')
    def test_float_vs_numeric(self):
        self._assert_diff(
            Column('data', Float()),
            Column('data', Numeric()),
            )

    @fixture.usedb()
    def test_numeric_precision(self):
        self._assert_diff(
            Column('data', Numeric(precision=5)),
            Column('data', Numeric(precision=6)),
            )

    @fixture.usedb()
    def test_numeric_scale(self):
        self._assert_diff(
            Column('data', Numeric(precision=6,scale=0)),
            Column('data', Numeric(precision=6,scale=1)),
            )

    @fixture.usedb()
    def test_string_length(self):
        self._assert_diff(
            Column('data', String(10)),
            Column('data', String(20)),
            )

    @fixture.usedb()
    def test_integer_identical(self):
        self._make_table(
            Column('data', Integer()),
            )
        diff = self._run_diff()
        self.assertEqual('No schema diffs',str(diff))
        self.assertFalse(diff)

    @fixture.usedb()
    def test_string_identical(self):
        self._make_table(
            Column('data', String(10)),
            )
        diff = self._run_diff()
        self.assertEqual('No schema diffs',str(diff))
        self.assertFalse(diff)

    @fixture.usedb()
    def test_text_identical(self):
        self._make_table(
            Column('data', Text),
            )
        diff = self._run_diff()
        self.assertEqual('No schema diffs',str(diff))
        self.assertFalse(diff)

class Test_getDiffOfModelAgainstModel(Test_getDiffOfModelAgainstDatabase):
    name1 = 'metadataA'
    name2 = 'metadataB'

    def _run_diff(self,**kw):
        db_meta= MetaData()
        db_meta.reflect(self.engine)
        return schemadiff.getDiffOfModelAgainstModel(
            self.meta, db_meta, **kw
            )
