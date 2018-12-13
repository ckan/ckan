#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlalchemy
import warnings

from sqlalchemy import *

from migrate import changeset, exceptions
from migrate.changeset import *
from migrate.changeset import constraint
from migrate.changeset.schema import ColumnDelta
from migrate.tests import fixture
from migrate.tests.fixture.warnings import catch_warnings
import six

class TestAddDropColumn(fixture.DB):
    """Test add/drop column through all possible interfaces
    also test for constraints
    """
    level = fixture.DB.CONNECT
    table_name = 'tmp_adddropcol'
    table_name_idx = 'tmp_adddropcol_idx'
    table_int = 0

    def _setup(self, url):
        super(TestAddDropColumn, self)._setup(url)
        self.meta = MetaData()
        self.table = Table(self.table_name, self.meta,
            Column('id', Integer, unique=True),
        )
        self.table_idx = Table(
            self.table_name_idx,
            self.meta,
            Column('id', Integer, primary_key=True),
            Column('a', Integer),
            Column('b', Integer),
            Index('test_idx', 'a', 'b')
        )
        self.meta.bind = self.engine
        if self.engine.has_table(self.table.name):
            self.table.drop()
        if self.engine.has_table(self.table_idx.name):
            self.table_idx.drop()
        self.table.create()
        self.table_idx.create()

    def _teardown(self):
        if self.engine.has_table(self.table.name):
            self.table.drop()
        if self.engine.has_table(self.table_idx.name):
            self.table_idx.drop()
        self.meta.clear()
        super(TestAddDropColumn,self)._teardown()

    def run_(self, create_column_func, drop_column_func, *col_p, **col_k):
        col_name = 'data'

        def assert_numcols(num_of_expected_cols):
            # number of cols should be correct in table object and in database
            self.refresh_table(self.table_name)
            result = len(self.table.c)

            self.assertEqual(result, num_of_expected_cols),
            if col_k.get('primary_key', None):
                # new primary key: check its length too
                result = len(self.table.primary_key)
                self.assertEqual(result, num_of_expected_cols)

        # we have 1 columns and there is no data column
        assert_numcols(1)
        self.assertTrue(getattr(self.table.c, 'data', None) is None)
        if len(col_p) == 0:
            col_p = [String(40)]
        col = Column(col_name, *col_p, **col_k)
        create_column_func(col)
        assert_numcols(2)
        # data column exists
        self.assertTrue(self.table.c.data.type.length, 40)

        col2 = self.table.c.data
        drop_column_func(col2)
        assert_numcols(1)

    @fixture.usedb()
    def test_undefined(self):
        """Add/drop columns not yet defined in the table"""
        def add_func(col):
            return create_column(col, self.table)
        def drop_func(col):
            return drop_column(col, self.table)
        return self.run_(add_func, drop_func)

    @fixture.usedb()
    def test_defined(self):
        """Add/drop columns already defined in the table"""
        def add_func(col):
            self.meta.clear()
            self.table = Table(self.table_name, self.meta,
                Column('id', Integer, primary_key=True),
                col,
            )
            return create_column(col)
        def drop_func(col):
            return drop_column(col)
        return self.run_(add_func, drop_func)

    @fixture.usedb()
    def test_method_bound(self):
        """Add/drop columns via column methods; columns bound to a table
        ie. no table parameter passed to function
        """
        def add_func(col):
            self.assertTrue(col.table is None, col.table)
            self.table.append_column(col)
            return col.create()
        def drop_func(col):
            #self.assertTrue(col.table is None,col.table)
            #self.table.append_column(col)
            return col.drop()
        return self.run_(add_func, drop_func)

    @fixture.usedb()
    def test_method_notbound(self):
        """Add/drop columns via column methods; columns not bound to a table"""
        def add_func(col):
            return col.create(self.table)
        def drop_func(col):
            return col.drop(self.table)
        return self.run_(add_func, drop_func)

    @fixture.usedb()
    def test_tablemethod_obj(self):
        """Add/drop columns via table methods; by column object"""
        def add_func(col):
            return self.table.create_column(col)
        def drop_func(col):
            return self.table.drop_column(col)
        return self.run_(add_func, drop_func)

    @fixture.usedb()
    def test_tablemethod_name(self):
        """Add/drop columns via table methods; by column name"""
        def add_func(col):
            # must be bound to table
            self.table.append_column(col)
            return self.table.create_column(col.name)
        def drop_func(col):
            # Not necessarily bound to table
            return self.table.drop_column(col.name)
        return self.run_(add_func, drop_func)

    @fixture.usedb()
    def test_byname(self):
        """Add/drop columns via functions; by table object and column name"""
        def add_func(col):
            self.table.append_column(col)
            return create_column(col.name, self.table)
        def drop_func(col):
            return drop_column(col.name, self.table)
        return self.run_(add_func, drop_func)

    @fixture.usedb()
    def test_drop_column_not_in_table(self):
        """Drop column by name"""
        def add_func(col):
            return self.table.create_column(col)
        def drop_func(col):
            if SQLA_07:
                self.table._columns.remove(col)
            else:
                self.table.c.remove(col)
            return self.table.drop_column(col.name)
        self.run_(add_func, drop_func)

    @fixture.usedb()
    def test_fk(self):
        """Can create columns with foreign keys"""
        # create FK's target
        reftable = Table('tmp_ref', self.meta,
            Column('id', Integer, primary_key=True),
        )
        if self.engine.has_table(reftable.name):
            reftable.drop()
        reftable.create()

        # create column with fk
        col = Column('data', Integer, ForeignKey(reftable.c.id, name='testfk'))
        col.create(self.table)

        # check if constraint is added
        for cons in self.table.constraints:
            if isinstance(cons, sqlalchemy.schema.ForeignKeyConstraint):
                break
        else:
            self.fail('No constraint found')

        # TODO: test on db level if constraints work

        if SQLA_07:
            self.assertEqual(reftable.c.id.name,
                list(col.foreign_keys)[0].column.name)
        else:
            self.assertEqual(reftable.c.id.name,
                col.foreign_keys[0].column.name)

        if self.engine.name == 'mysql':
            constraint.ForeignKeyConstraint([self.table.c.data],
                                            [reftable.c.id],
                                            name='testfk').drop()
        col.drop(self.table)

        if self.engine.has_table(reftable.name):
            reftable.drop()

    @fixture.usedb(not_supported='sqlite')
    def test_pk(self):
        """Can create columns with primary key"""
        col = Column('data', Integer, nullable=False)
        self.assertRaises(exceptions.InvalidConstraintError,
            col.create, self.table, primary_key_name=True)
        col.create(self.table, primary_key_name='data_pkey')

        # check if constraint was added (cannot test on objects)
        self.table.insert(values={'data': 4}).execute()
        try:
            self.table.insert(values={'data': 4}).execute()
        except (sqlalchemy.exc.IntegrityError,
                sqlalchemy.exc.ProgrammingError):
            pass
        else:
            self.fail()

        col.drop()

    @fixture.usedb(not_supported=['mysql'])
    def test_check(self):
        """Can create columns with check constraint"""
        col = Column('foo',
                     Integer,
                     sqlalchemy.schema.CheckConstraint('foo > 4'))
        col.create(self.table)

        # check if constraint was added (cannot test on objects)
        self.table.insert(values={'foo': 5}).execute()
        try:
            self.table.insert(values={'foo': 3}).execute()
        except (sqlalchemy.exc.IntegrityError,
                sqlalchemy.exc.ProgrammingError):
            pass
        else:
            self.fail()

        col.drop()

    @fixture.usedb()
    def test_unique_constraint(self):
        self.assertRaises(exceptions.InvalidConstraintError,
            Column('data', Integer, unique=True).create, self.table)

        col = Column('data', Integer)
        col.create(self.table, unique_name='data_unique')

        # check if constraint was added (cannot test on objects)
        self.table.insert(values={'data': 5}).execute()
        try:
            self.table.insert(values={'data': 5}).execute()
        except (sqlalchemy.exc.IntegrityError,
                sqlalchemy.exc.ProgrammingError):
            pass
        else:
            self.fail()

        col.drop(self.table)

# TODO: remove already attached columns with uniques, pks, fks ..
    @fixture.usedb(not_supported=['ibm_db_sa', 'postgresql'])
    def test_drop_column_of_composite_index(self):
        # NOTE(rpodolyaka): postgresql automatically drops a composite index
        #                   if one of its columns is dropped
        # NOTE(mriedem): DB2 does the same.
        self.table_idx.c.b.drop()

        reflected = Table(self.table_idx.name, MetaData(), autoload=True,
                          autoload_with=self.engine)
        index = next(iter(reflected.indexes))
        self.assertEquals(['a'], [c.name for c in index.columns])

    @fixture.usedb()
    def test_drop_all_columns_of_composite_index(self):
        self.table_idx.c.a.drop()
        self.table_idx.c.b.drop()

        reflected = Table(self.table_idx.name, MetaData(), autoload=True,
                          autoload_with=self.engine)
        self.assertEquals(0, len(reflected.indexes))

    def _check_index(self,expected):
        if 'mysql' in self.engine.name or 'postgres' in self.engine.name:
            for index in tuple(
                Table(self.table.name, MetaData(),
                      autoload=True, autoload_with=self.engine).indexes
                ):
                if index.name=='ix_data':
                    break
            self.assertEqual(expected,index.unique)

    @fixture.usedb()
    def test_index(self):
        col = Column('data', Integer)
        col.create(self.table, index_name='ix_data')

        self._check_index(False)

        col.drop()

    @fixture.usedb()
    def test_index_unique(self):
        # shows how to create a unique index
        col = Column('data', Integer)
        col.create(self.table)
        Index('ix_data', col, unique=True).create(bind=self.engine)

        # check if index was added
        self.table.insert(values={'data': 5}).execute()
        try:
            self.table.insert(values={'data': 5}).execute()
        except (sqlalchemy.exc.IntegrityError,
                sqlalchemy.exc.ProgrammingError):
            pass
        else:
            self.fail()

        self._check_index(True)

        col.drop()

    @fixture.usedb()
    def test_server_defaults(self):
        """Can create columns with server_default values"""
        col = Column('data', String(244), server_default='foobar')
        col.create(self.table)

        self.table.insert(values={'id': 10}).execute()
        row = self._select_row()
        self.assertEqual(u'foobar', row['data'])

        col.drop()

    @fixture.usedb()
    def test_populate_default(self):
        """Test populate_default=True"""
        def default():
            return 'foobar'
        col = Column('data', String(244), default=default)
        col.create(self.table, populate_default=True)

        self.table.insert(values={'id': 10}).execute()
        row = self._select_row()
        self.assertEqual(u'foobar', row['data'])

        col.drop()

    # TODO: test sequence
    # TODO: test quoting
    # TODO: test non-autoname constraints

    @fixture.usedb()
    def test_drop_doesnt_delete_other_indexes(self):
        # add two indexed columns
        self.table.drop()
        self.meta.clear()
        self.table = Table(
            self.table_name, self.meta,
            Column('id', Integer, primary_key=True),
            Column('d1', String(10), index=True),
            Column('d2', String(10), index=True),
            )
        self.table.create()

        # paranoid check
        self.refresh_table()
        self.assertEqual(
            sorted([i.name for i in self.table.indexes]),
            [u'ix_tmp_adddropcol_d1', u'ix_tmp_adddropcol_d2']
            )

        # delete one
        self.table.c.d2.drop()

        # ensure the other index is still there
        self.refresh_table()
        self.assertEqual(
            sorted([i.name for i in self.table.indexes]),
            [u'ix_tmp_adddropcol_d1']
            )

    def _actual_foreign_keys(self):
        from sqlalchemy.schema import ForeignKeyConstraint
        result = []
        for cons in self.table.constraints:
            if isinstance(cons,ForeignKeyConstraint):
                col_names = []
                for col_name in cons.columns:
                    if not isinstance(col_name,six.string_types):
                        col_name = col_name.name
                    col_names.append(col_name)
                result.append(col_names)
        result.sort()
        return result

    @fixture.usedb()
    def test_drop_with_foreign_keys(self):
        self.table.drop()
        self.meta.clear()

        # create FK's target
        reftable = Table('tmp_ref', self.meta,
            Column('id', Integer, primary_key=True),
        )
        if self.engine.has_table(reftable.name):
            reftable.drop()
        reftable.create()

        # add a table with two foreign key columns
        self.table = Table(
            self.table_name, self.meta,
            Column('id', Integer, primary_key=True),
            Column('r1', Integer, ForeignKey('tmp_ref.id', name='test_fk1')),
            Column('r2', Integer, ForeignKey('tmp_ref.id', name='test_fk2')),
            )
        self.table.create()

        # paranoid check
        self.assertEqual([['r1'],['r2']],
                         self._actual_foreign_keys())

        # delete one
        if self.engine.name == 'mysql':
            constraint.ForeignKeyConstraint([self.table.c.r2], [reftable.c.id],
                                            name='test_fk2').drop()
        self.table.c.r2.drop()

        # check remaining foreign key is there
        self.assertEqual([['r1']],
                         self._actual_foreign_keys())

    @fixture.usedb()
    def test_drop_with_complex_foreign_keys(self):
        from sqlalchemy.schema import ForeignKeyConstraint
        from sqlalchemy.schema import UniqueConstraint

        self.table.drop()
        self.meta.clear()

        # NOTE(mriedem): DB2 does not currently support unique constraints
        # on nullable columns, so the columns that are used to create the
        # foreign keys here need to be non-nullable for testing with DB2
        # to work.

        # create FK's target
        reftable = Table('tmp_ref', self.meta,
            Column('id', Integer, primary_key=True),
            Column('jd', Integer, nullable=False),
            UniqueConstraint('id','jd')
            )
        if self.engine.has_table(reftable.name):
            reftable.drop()
        reftable.create()

        # add a table with a complex foreign key constraint
        self.table = Table(
            self.table_name, self.meta,
            Column('id', Integer, primary_key=True),
            Column('r1', Integer, nullable=False),
            Column('r2', Integer, nullable=False),
            ForeignKeyConstraint(['r1','r2'],
                                 [reftable.c.id,reftable.c.jd],
                                 name='test_fk')
            )
        self.table.create()

        # paranoid check
        self.assertEqual([['r1','r2']],
                         self._actual_foreign_keys())

        # delete one
        if self.engine.name == 'mysql':
            constraint.ForeignKeyConstraint([self.table.c.r1, self.table.c.r2],
                                            [reftable.c.id, reftable.c.jd],
                                            name='test_fk').drop()
        self.table.c.r2.drop()

        # check the constraint is gone, since part of it
        # is no longer there - if people hit this,
        # they may be confused, maybe we should raise an error
        # and insist that the constraint is deleted first, separately?
        self.assertEqual([],
                         self._actual_foreign_keys())

class TestRename(fixture.DB):
    """Tests for table and index rename methods"""
    level = fixture.DB.CONNECT
    meta = MetaData()

    def _setup(self, url):
        super(TestRename, self)._setup(url)
        self.meta.bind = self.engine

    @fixture.usedb(not_supported='firebird')
    def test_rename_table(self):
        """Tables can be renamed"""
        c_name = 'col_1'
        table_name1 = 'name_one'
        table_name2 = 'name_two'
        index_name1 = 'x' + table_name1
        index_name2 = 'x' + table_name2

        self.meta.clear()
        self.column = Column(c_name, Integer)
        self.table = Table(table_name1, self.meta, self.column)
        self.index = Index(index_name1, self.column, unique=False)

        if self.engine.has_table(self.table.name):
            self.table.drop()
        if self.engine.has_table(table_name2):
            tmp = Table(table_name2, self.meta, autoload=True)
            tmp.drop()
            tmp.deregister()
            del tmp
        self.table.create()

        def assert_table_name(expected, skip_object_check=False):
            """Refresh a table via autoload
            SA has changed some since this test was written; we now need to do
            meta.clear() upon reloading a table - clear all rather than a
            select few. So, this works only if we're working with one table at
            a time (else, others will vanish too).
            """
            if not skip_object_check:
                # Table object check
                self.assertEqual(self.table.name,expected)
                newname = self.table.name
            else:
                # we know the object's name isn't consistent: just assign it
                newname = expected
            # Table DB check
            self.meta.clear()
            self.table = Table(newname, self.meta, autoload=True)
            self.assertEqual(self.table.name, expected)

        def assert_index_name(expected, skip_object_check=False):
            if not skip_object_check:
                # Index object check
                self.assertEqual(self.index.name, expected)
            else:
                # object is inconsistent
                self.index.name = expected
            # TODO: Index DB check

        def add_table_to_meta(name):
            # trigger the case where table_name2 needs to be
            # removed from the metadata in ChangesetTable.deregister()
            tmp = Table(name, self.meta, Column(c_name, Integer))
            tmp.create()
            tmp.drop()

        try:
            # Table renames
            assert_table_name(table_name1)
            add_table_to_meta(table_name2)
            rename_table(self.table, table_name2)
            assert_table_name(table_name2)
            self.table.rename(table_name1)
            assert_table_name(table_name1)

            # test by just the string
            rename_table(table_name1, table_name2, engine=self.engine)
            assert_table_name(table_name2, True)   # object not updated

            # Index renames
            if self.url.startswith('sqlite') or self.url.startswith('mysql'):
                self.assertRaises(exceptions.NotSupportedError,
                    self.index.rename, index_name2)
            else:
                assert_index_name(index_name1)
                rename_index(self.index, index_name2, engine=self.engine)
                assert_index_name(index_name2)
                self.index.rename(index_name1)
                assert_index_name(index_name1)

                # test by just the string
                rename_index(index_name1, index_name2, engine=self.engine)
                assert_index_name(index_name2, True)

        finally:
            if self.table.exists():
                self.table.drop()


class TestColumnChange(fixture.DB):
    level = fixture.DB.CONNECT
    table_name = 'tmp_colchange'

    def _setup(self, url):
        super(TestColumnChange, self)._setup(url)
        self.meta = MetaData(self.engine)
        self.table = Table(self.table_name, self.meta,
            Column('id', Integer, primary_key=True),
            Column('data', String(40), server_default=DefaultClause("tluafed"),
                   nullable=True),
        )
        if self.table.exists():
            self.table.drop()
        try:
            self.table.create()
        except sqlalchemy.exc.SQLError:
            # SQLite: database schema has changed
            if not self.url.startswith('sqlite://'):
                raise

    def _teardown(self):
        if self.table.exists():
            try:
                self.table.drop(self.engine)
            except sqlalchemy.exc.SQLError:
                # SQLite: database schema has changed
                if not self.url.startswith('sqlite://'):
                    raise
        super(TestColumnChange, self)._teardown()

    @fixture.usedb()
    def test_rename(self):
        """Can rename a column"""
        def num_rows(col, content):
            return len(list(self.table.select(col == content).execute()))
        # Table content should be preserved in changed columns
        content = "fgsfds"
        self.engine.execute(self.table.insert(), data=content, id=42)
        self.assertEqual(num_rows(self.table.c.data, content), 1)

        # ...as a function, given a column object and the new name
        alter_column('data', name='data2', table=self.table)
        self.refresh_table()
        alter_column(self.table.c.data2, name='atad')
        self.refresh_table(self.table.name)
        self.assertTrue('data' not in self.table.c.keys())
        self.assertTrue('atad' in self.table.c.keys())
        self.assertEqual(num_rows(self.table.c.atad, content), 1)

        # ...as a method, given a new name
        self.table.c.atad.alter(name='data')
        self.refresh_table(self.table.name)
        self.assertTrue('atad' not in self.table.c.keys())
        self.table.c.data # Should not raise exception
        self.assertEqual(num_rows(self.table.c.data, content), 1)

        # ...as a function, given a new object
        alter_column(self.table.c.data,
                     name = 'atad', type=String(40),
                     server_default=self.table.c.data.server_default)
        self.refresh_table(self.table.name)
        self.assertTrue('data' not in self.table.c.keys())
        self.table.c.atad   # Should not raise exception
        self.assertEqual(num_rows(self.table.c.atad, content), 1)

        # ...as a method, given a new object
        self.table.c.atad.alter(
            name='data',type=String(40),
            server_default=self.table.c.atad.server_default
            )
        self.refresh_table(self.table.name)
        self.assertTrue('atad' not in self.table.c.keys())
        self.table.c.data   # Should not raise exception
        self.assertEqual(num_rows(self.table.c.data,content), 1)

    @fixture.usedb()
    def test_type(self):
        # Test we can change a column's type

        # Just the new type
        self.table.c.data.alter(type=String(43))
        self.refresh_table(self.table.name)
        self.assertTrue(isinstance(self.table.c.data.type, String))
        self.assertEqual(self.table.c.data.type.length, 43)

        # Different type
        self.assertTrue(isinstance(self.table.c.id.type, Integer))
        self.assertEqual(self.table.c.id.nullable, False)

        if not self.engine.name == 'firebird':
            self.table.c.id.alter(type=String(20))
            self.assertEqual(self.table.c.id.nullable, False)
            self.refresh_table(self.table.name)
            self.assertTrue(isinstance(self.table.c.id.type, String))

    @fixture.usedb()
    def test_default(self):
        """Can change a column's server_default value (DefaultClauses only)
        Only DefaultClauses are changed here: others are managed by the
        application / by SA
        """
        self.assertEqual(self.table.c.data.server_default.arg, 'tluafed')

        # Just the new default
        default = 'my_default'
        self.table.c.data.alter(server_default=DefaultClause(default))
        self.refresh_table(self.table.name)
        #self.assertEqual(self.table.c.data.server_default.arg,default)
        # TextClause returned by autoload
        self.assertTrue(default in str(self.table.c.data.server_default.arg))
        self.engine.execute(self.table.insert(), id=12)
        row = self._select_row()
        self.assertEqual(row['data'], default)

        # Column object
        default = 'your_default'
        self.table.c.data.alter(type=String(40), server_default=DefaultClause(default))
        self.refresh_table(self.table.name)
        self.assertTrue(default in str(self.table.c.data.server_default.arg))

        # Drop/remove default
        self.table.c.data.alter(server_default=None)
        self.assertEqual(self.table.c.data.server_default, None)

        self.refresh_table(self.table.name)
        # server_default isn't necessarily None for Oracle
        #self.assertTrue(self.table.c.data.server_default is None,self.table.c.data.server_default)
        self.engine.execute(self.table.insert(), id=11)
        row = self.table.select(self.table.c.id == 11).execution_options(autocommit=True).execute().fetchone()
        self.assertTrue(row['data'] is None, row['data'])

    @fixture.usedb(not_supported='firebird')
    def test_null(self):
        """Can change a column's null constraint"""
        self.assertEqual(self.table.c.data.nullable, True)

        # Full column
        self.table.c.data.alter(type=String(40), nullable=False)
        self.table.nullable = None
        self.refresh_table(self.table.name)
        self.assertEqual(self.table.c.data.nullable, False)

        # Just the new status
        self.table.c.data.alter(nullable=True)
        self.refresh_table(self.table.name)
        self.assertEqual(self.table.c.data.nullable, True)

    @fixture.usedb()
    def test_alter_deprecated(self):
        try:
            # py 2.4 compatability :-/
            cw = catch_warnings(record=True)
            w = cw.__enter__()

            warnings.simplefilter("always")
            self.table.c.data.alter(Column('data', String(100)))

            self.assertEqual(len(w),1)
            self.assertTrue(issubclass(w[-1].category,
                                       MigrateDeprecationWarning))
            self.assertEqual(
                'Passing a Column object to alter_column is deprecated. '
                'Just pass in keyword parameters instead.',
                str(w[-1].message))
        finally:
            cw.__exit__()

    @fixture.usedb()
    def test_alter_returns_delta(self):
        """Test if alter constructs return delta"""

        delta = self.table.c.data.alter(type=String(100))
        self.assertTrue('type' in delta)

    @fixture.usedb()
    def test_alter_all(self):
        """Tests all alter changes at one time"""
        # test for each db separately
        # since currently some dont support everything

        # test pre settings
        self.assertEqual(self.table.c.data.nullable, True)
        self.assertEqual(self.table.c.data.server_default.arg, 'tluafed')
        self.assertEqual(self.table.c.data.name, 'data')
        self.assertTrue(isinstance(self.table.c.data.type, String))
        self.assertTrue(self.table.c.data.type.length, 40)

        kw = dict(nullable=False,
                 server_default='foobar',
                 name='data_new',
                 type=String(50))
        if self.engine.name == 'firebird':
            del kw['nullable']
        self.table.c.data.alter(**kw)

        # test altered objects
        self.assertEqual(self.table.c.data.server_default.arg, 'foobar')
        if not self.engine.name == 'firebird':
            self.assertEqual(self.table.c.data.nullable, False)
        self.assertEqual(self.table.c.data.name, 'data_new')
        self.assertEqual(self.table.c.data.type.length, 50)

        self.refresh_table(self.table.name)

        # test post settings
        if not self.engine.name == 'firebird':
            self.assertEqual(self.table.c.data_new.nullable, False)
        self.assertEqual(self.table.c.data_new.name, 'data_new')
        self.assertTrue(isinstance(self.table.c.data_new.type, String))
        self.assertTrue(self.table.c.data_new.type.length, 50)

        # insert data and assert default
        self.table.insert(values={'id': 10}).execute()
        row = self._select_row()
        self.assertEqual(u'foobar', row['data_new'])


class TestColumnDelta(fixture.DB):
    """Tests ColumnDelta class"""

    level = fixture.DB.CONNECT
    table_name = 'tmp_coldelta'
    table_int = 0

    def _setup(self, url):
        super(TestColumnDelta, self)._setup(url)
        self.meta = MetaData()
        self.table = Table(self.table_name, self.meta,
            Column('ids', String(10)),
        )
        self.meta.bind = self.engine
        if self.engine.has_table(self.table.name):
            self.table.drop()
        self.table.create()

    def _teardown(self):
        if self.engine.has_table(self.table.name):
            self.table.drop()
        self.meta.clear()
        super(TestColumnDelta,self)._teardown()

    def mkcol(self, name='id', type=String, *p, **k):
        return Column(name, type, *p, **k)

    def verify(self, expected, original, *p, **k):
        self.delta = ColumnDelta(original, *p, **k)
        result = list(self.delta.keys())
        result.sort()
        self.assertEqual(expected, result)
        return self.delta

    def test_deltas_two_columns(self):
        """Testing ColumnDelta with two columns"""
        col_orig = self.mkcol(primary_key=True)
        col_new = self.mkcol(name='ids', primary_key=True)
        self.verify([], col_orig, col_orig)
        self.verify(['name'], col_orig, col_orig, 'ids')
        self.verify(['name'], col_orig, col_orig, name='ids')
        self.verify(['name'], col_orig, col_new)
        self.verify(['name', 'type'], col_orig, col_new, type=String)

        # Type comparisons
        self.verify([], self.mkcol(type=String), self.mkcol(type=String))
        self.verify(['type'], self.mkcol(type=String), self.mkcol(type=Integer))
        self.verify(['type'], self.mkcol(type=String), self.mkcol(type=String(42)))
        self.verify([], self.mkcol(type=String(42)), self.mkcol(type=String(42)))
        self.verify(['type'], self.mkcol(type=String(24)), self.mkcol(type=String(42)))
        self.verify(['type'], self.mkcol(type=String(24)), self.mkcol(type=Text(24)))

        # Other comparisons
        self.verify(['primary_key'], self.mkcol(nullable=False), self.mkcol(primary_key=True))

        # PK implies nullable=False
        self.verify(['nullable', 'primary_key'], self.mkcol(nullable=True), self.mkcol(primary_key=True))
        self.verify([], self.mkcol(primary_key=True), self.mkcol(primary_key=True))
        self.verify(['nullable'], self.mkcol(nullable=True), self.mkcol(nullable=False))
        self.verify([], self.mkcol(nullable=True), self.mkcol(nullable=True))
        self.verify([], self.mkcol(server_default=None), self.mkcol(server_default=None))
        self.verify([], self.mkcol(server_default='42'), self.mkcol(server_default='42'))

        # test server default
        delta = self.verify(['server_default'], self.mkcol(), self.mkcol('id', String, DefaultClause('foobar')))
        self.assertEqual(delta['server_default'].arg, 'foobar')

        self.verify([], self.mkcol(server_default='foobar'), self.mkcol('id', String, DefaultClause('foobar')))
        self.verify(['type'], self.mkcol(server_default='foobar'), self.mkcol('id', Text, DefaultClause('foobar')))

        col = self.mkcol(server_default='foobar')
        self.verify(['type'], col, self.mkcol('id', Text, DefaultClause('foobar')), alter_metadata=True)
        self.assertTrue(isinstance(col.type, Text))

        col = self.mkcol()
        self.verify(['name', 'server_default', 'type'], col, self.mkcol('beep', Text, DefaultClause('foobar')),
                    alter_metadata=True)
        self.assertTrue(isinstance(col.type, Text))
        self.assertEqual(col.name, 'beep')
        self.assertEqual(col.server_default.arg, 'foobar')

    @fixture.usedb()
    def test_deltas_zero_columns(self):
        """Testing ColumnDelta with zero columns"""

        self.verify(['name'], 'ids', table=self.table, name='hey')

        # test reflection
        self.verify(['type'], 'ids', table=self.table.name, type=String(80), engine=self.engine)
        self.verify(['type'], 'ids', table=self.table.name, type=String(80), metadata=self.meta)

        self.meta.clear()
        delta = self.verify(['type'], 'ids', table=self.table.name, type=String(80), metadata=self.meta,
                            alter_metadata=True)
        self.assertTrue(self.table.name in self.meta)
        self.assertEqual(delta.result_column.type.length, 80)
        self.assertEqual(self.meta.tables.get(self.table.name).c.ids.type.length, 80)

        # test defaults
        self.meta.clear()
        self.verify(['server_default'], 'ids', table=self.table.name, server_default='foobar',
                    metadata=self.meta,
                    alter_metadata=True)
        self.meta.tables.get(self.table.name).c.ids.server_default.arg == 'foobar'

        # test missing parameters
        self.assertRaises(ValueError, ColumnDelta, table=self.table.name)
        self.assertRaises(ValueError, ColumnDelta, 'ids', table=self.table.name, alter_metadata=True)
        self.assertRaises(ValueError, ColumnDelta, 'ids', table=self.table.name, alter_metadata=False)

    def test_deltas_one_column(self):
        """Testing ColumnDelta with one column"""
        col_orig = self.mkcol(primary_key=True)

        self.verify([], col_orig)
        self.verify(['name'], col_orig, 'ids')
        # Parameters are always executed, even if they're 'unchanged'
        # (We can't assume given column is up-to-date)
        self.verify(['name', 'primary_key', 'type'], col_orig, 'id', Integer, primary_key=True)
        self.verify(['name', 'primary_key', 'type'], col_orig, name='id', type=Integer, primary_key=True)

        # Change name, given an up-to-date definition and the current name
        delta = self.verify(['name'], col_orig, name='blah')
        self.assertEqual(delta.get('name'), 'blah')
        self.assertEqual(delta.current_name, 'id')

        col_orig = self.mkcol(primary_key=True)
        self.verify(['name', 'type'], col_orig, name='id12', type=Text, alter_metadata=True)
        self.assertTrue(isinstance(col_orig.type, Text))
        self.assertEqual(col_orig.name, 'id12')

        # test server default
        col_orig = self.mkcol(primary_key=True)
        delta = self.verify(['server_default'], col_orig, DefaultClause('foobar'))
        self.assertEqual(delta['server_default'].arg, 'foobar')

        delta = self.verify(['server_default'], col_orig, server_default=DefaultClause('foobar'))
        self.assertEqual(delta['server_default'].arg, 'foobar')

        # no change
        col_orig = self.mkcol(server_default=DefaultClause('foobar'))
        delta = self.verify(['type'], col_orig, DefaultClause('foobar'), type=PickleType)
        self.assertTrue(isinstance(delta.result_column.type, PickleType))

        # TODO: test server on update
        # TODO: test bind metadata
