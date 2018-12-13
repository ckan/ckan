#!/usr/bin/env python
# -*- coding: utf-8 -*-

import imp
import os
import sys
import shutil

import six
from migrate import exceptions
from migrate.versioning import version, repository
from migrate.versioning.script import *
from migrate.versioning.util import *

from migrate.tests import fixture
from migrate.tests.fixture.models import tmp_sql_table


class TestBaseScript(fixture.Pathed):

    def test_all(self):
        """Testing all basic BaseScript operations"""
        # verify / source / run
        src = self.tmp()
        open(src, 'w').close()
        bscript = BaseScript(src)
        BaseScript.verify(src)
        self.assertEqual(bscript.source(), '')
        self.assertRaises(NotImplementedError, bscript.run, 'foobar')


class TestPyScript(fixture.Pathed, fixture.DB):
    cls = PythonScript
    def test_create(self):
        """We can create a migration script"""
        path = self.tmp_py()
        # Creating a file that doesn't exist should succeed
        self.cls.create(path)
        self.assertTrue(os.path.exists(path))
        # Created file should be a valid script (If not, raises an error)
        self.cls.verify(path)
        # Can't create it again: it already exists
        self.assertRaises(exceptions.PathFoundError,self.cls.create,path)

    @fixture.usedb(supported='sqlite')
    def test_run(self):
        script_path = self.tmp_py()
        pyscript = PythonScript.create(script_path)
        pyscript.run(self.engine, 1)
        pyscript.run(self.engine, -1)

        self.assertRaises(exceptions.ScriptError, pyscript.run, self.engine, 0)
        self.assertRaises(exceptions.ScriptError, pyscript._func, 'foobar')

        # clean pyc file
        if six.PY3:
            os.remove(imp.cache_from_source(script_path))
        else:
            os.remove(script_path + 'c')

        # test deprecated upgrade/downgrade with no arguments
        contents = open(script_path, 'r').read()
        f = open(script_path, 'w')
        f.write(contents.replace("upgrade(migrate_engine)", "upgrade()"))
        f.close()

        pyscript = PythonScript(script_path)
        pyscript._module = None
        try:
            pyscript.run(self.engine, 1)
            pyscript.run(self.engine, -1)
        except exceptions.ScriptError:
            pass
        else:
            self.fail()

    def test_verify_notfound(self):
        """Correctly verify a python migration script: nonexistant file"""
        path = self.tmp_py()
        self.assertFalse(os.path.exists(path))
        # Fails on empty path
        self.assertRaises(exceptions.InvalidScriptError,self.cls.verify,path)
        self.assertRaises(exceptions.InvalidScriptError,self.cls,path)

    def test_verify_invalidpy(self):
        """Correctly verify a python migration script: invalid python file"""
        path=self.tmp_py()
        # Create empty file
        f = open(path,'w')
        f.write("def fail")
        f.close()
        self.assertRaises(Exception,self.cls.verify_module,path)
        # script isn't verified on creation, but on module reference
        py = self.cls(path)
        self.assertRaises(Exception,(lambda x: x.module),py)

    def test_verify_nofuncs(self):
        """Correctly verify a python migration script: valid python file; no upgrade func"""
        path = self.tmp_py()
        # Create empty file
        f = open(path, 'w')
        f.write("def zergling():\n\tprint('rush')")
        f.close()
        self.assertRaises(exceptions.InvalidScriptError, self.cls.verify_module, path)
        # script isn't verified on creation, but on module reference
        py = self.cls(path)
        self.assertRaises(exceptions.InvalidScriptError,(lambda x: x.module),py)

    @fixture.usedb(supported='sqlite')
    def test_preview_sql(self):
        """Preview SQL abstract from ORM layer (sqlite)"""
        path = self.tmp_py()

        f = open(path, 'w')
        content = '''
from migrate import *
from sqlalchemy import *

metadata = MetaData()

UserGroup = Table('Link', metadata,
    Column('link1ID', Integer),
    Column('link2ID', Integer),
    UniqueConstraint('link1ID', 'link2ID'))

def upgrade(migrate_engine):
    metadata.create_all(migrate_engine)
        '''
        f.write(content)
        f.close()

        pyscript = self.cls(path)
        SQL = pyscript.preview_sql(self.url, 1)
        self.assertEqualIgnoreWhitespace("""
        CREATE TABLE "Link"
        ("link1ID" INTEGER,
        "link2ID" INTEGER,
        UNIQUE ("link1ID", "link2ID"))
        """, SQL)
        # TODO: test: No SQL should be executed!

    def test_verify_success(self):
        """Correctly verify a python migration script: success"""
        path = self.tmp_py()
        # Succeeds after creating
        self.cls.create(path)
        self.cls.verify(path)

    # test for PythonScript.make_update_script_for_model

    @fixture.usedb()
    def test_make_update_script_for_model(self):
        """Construct script source from differences of two models"""

        self.setup_model_params()
        self.write_file(self.first_model_path, self.base_source)
        self.write_file(self.second_model_path, self.base_source + self.model_source)

        source_script = self.pyscript.make_update_script_for_model(
            engine=self.engine,
            oldmodel=load_model('testmodel_first:meta'),
            model=load_model('testmodel_second:meta'),
            repository=self.repo_path,
        )

        self.assertTrue("['User'].create()" in source_script)
        self.assertTrue("['User'].drop()" in source_script)

    @fixture.usedb()
    def test_make_update_script_for_equal_models(self):
        """Try to make update script from two identical models"""

        self.setup_model_params()
        self.write_file(self.first_model_path, self.base_source + self.model_source)
        self.write_file(self.second_model_path, self.base_source + self.model_source)

        source_script = self.pyscript.make_update_script_for_model(
            engine=self.engine,
            oldmodel=load_model('testmodel_first:meta'),
            model=load_model('testmodel_second:meta'),
            repository=self.repo_path,
        )

        self.assertFalse('User.create()' in source_script)
        self.assertFalse('User.drop()' in source_script)

    @fixture.usedb()
    def test_make_update_script_direction(self):
        """Check update scripts go in the right direction"""

        self.setup_model_params()
        self.write_file(self.first_model_path, self.base_source)
        self.write_file(self.second_model_path, self.base_source + self.model_source)

        source_script = self.pyscript.make_update_script_for_model(
            engine=self.engine,
            oldmodel=load_model('testmodel_first:meta'),
            model=load_model('testmodel_second:meta'),
            repository=self.repo_path,
        )

        self.assertTrue(0
                        < source_script.find('upgrade')
                        < source_script.find("['User'].create()")
                        < source_script.find('downgrade')
                        < source_script.find("['User'].drop()"))

    def setup_model_params(self):
        self.script_path = self.tmp_py()
        self.repo_path = self.tmp()
        self.first_model_path = os.path.join(self.temp_usable_dir, 'testmodel_first.py')
        self.second_model_path = os.path.join(self.temp_usable_dir, 'testmodel_second.py')

        self.base_source = """from sqlalchemy import *\nmeta = MetaData()\n"""
        self.model_source = """
User = Table('User', meta,
    Column('id', Integer, primary_key=True),
    Column('login', Unicode(40)),
    Column('passwd', String(40)),
)"""

        self.repo = repository.Repository.create(self.repo_path, 'repo')
        self.pyscript = PythonScript.create(self.script_path)
        sys.modules.pop('testmodel_first', None)
        sys.modules.pop('testmodel_second', None)

    def write_file(self, path, contents):
        f = open(path, 'w')
        f.write(contents)
        f.close()


class TestSqlScript(fixture.Pathed, fixture.DB):

    @fixture.usedb()
    def test_error(self):
        """Test if exception is raised on wrong script source"""
        src = self.tmp()

        f = open(src, 'w')
        f.write("""foobar""")
        f.close()

        sqls = SqlScript(src)
        self.assertRaises(Exception, sqls.run, self.engine)

    @fixture.usedb()
    def test_success(self):
        """Test sucessful SQL execution"""
        # cleanup and prepare python script
        tmp_sql_table.metadata.drop_all(self.engine, checkfirst=True)
        script_path = self.tmp_py()
        pyscript = PythonScript.create(script_path)

        # populate python script
        contents = open(script_path, 'r').read()
        contents = contents.replace("pass", "tmp_sql_table.create(migrate_engine)")
        contents = 'from migrate.tests.fixture.models import tmp_sql_table\n' + contents
        f = open(script_path, 'w')
        f.write(contents)
        f.close()

        # write SQL script from python script preview
        pyscript = PythonScript(script_path)
        src = self.tmp()
        f = open(src, 'w')
        f.write(pyscript.preview_sql(self.url, 1))
        f.close()

        # run the change
        sqls = SqlScript(src)
        sqls.run(self.engine)
        tmp_sql_table.metadata.drop_all(self.engine, checkfirst=True)

    @fixture.usedb()
    def test_transaction_management_statements(self):
        """
        Test that we can successfully execute SQL scripts with transaction
        management statements.
        """
        for script_pattern in (
            "BEGIN TRANSACTION; %s; COMMIT;",
            "BEGIN; %s; END TRANSACTION;",
            "/* comment */BEGIN TRANSACTION; %s; /* comment */COMMIT;",
            "/* comment */ BEGIN TRANSACTION; %s; /* comment */ COMMIT;",
            """
-- comment
BEGIN TRANSACTION;

%s;

-- comment
COMMIT;""",
        ):

            test_statement = ("CREATE TABLE TEST1 (field1 int); "
                              "DROP TABLE TEST1")
            script = script_pattern % test_statement
            src = self.tmp()

            with open(src, 'wt') as f:
                f.write(script)

            sqls = SqlScript(src)
            sqls.run(self.engine)
