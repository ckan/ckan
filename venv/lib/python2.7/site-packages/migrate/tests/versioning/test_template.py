#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil

import migrate.versioning.templates
from migrate.versioning.template import *
from migrate.versioning import api

from migrate.tests import fixture


class TestTemplate(fixture.Pathed):
    def test_templates(self):
        """We can find the path to all repository templates"""
        path = str(Template())
        self.assertTrue(os.path.exists(path))

    def test_repository(self):
        """We can find the path to the default repository"""
        path = Template().get_repository()
        self.assertTrue(os.path.exists(path))

    def test_script(self):
        """We can find the path to the default migration script"""
        path = Template().get_script()
        self.assertTrue(os.path.exists(path))

    def test_custom_templates_and_themes(self):
        """Users can define their own templates with themes"""
        new_templates_dir = os.path.join(self.temp_usable_dir, 'templates')
        manage_tmpl_file = os.path.join(new_templates_dir, 'manage/custom.py_tmpl')
        repository_tmpl_file = os.path.join(new_templates_dir, 'repository/custom/README')
        script_tmpl_file = os.path.join(new_templates_dir, 'script/custom.py_tmpl')
        sql_script_tmpl_file = os.path.join(new_templates_dir, 'sql_script/custom.py_tmpl')

        MANAGE_CONTENTS = 'print "manage.py"'
        README_CONTENTS = 'MIGRATE README!'
        SCRIPT_FILE_CONTENTS = 'print "script.py"'
        new_repo_dest = self.tmp_repos()
        new_manage_dest = self.tmp_py()

        # make new templates dir
        shutil.copytree(migrate.versioning.templates.__path__[0], new_templates_dir)
        shutil.copytree(os.path.join(new_templates_dir, 'repository/default'),
            os.path.join(new_templates_dir, 'repository/custom'))

        # edit templates
        f = open(manage_tmpl_file, 'w').write(MANAGE_CONTENTS)
        f = open(repository_tmpl_file, 'w').write(README_CONTENTS)
        f = open(script_tmpl_file, 'w').write(SCRIPT_FILE_CONTENTS)
        f = open(sql_script_tmpl_file, 'w').write(SCRIPT_FILE_CONTENTS)

        # create repository, manage file and python script
        kw = {}
        kw['templates_path'] = new_templates_dir
        kw['templates_theme'] = 'custom'
        api.create(new_repo_dest, 'repo_name', **kw)
        api.script('test', new_repo_dest, **kw)
        api.script_sql('postgres', 'foo', new_repo_dest, **kw)
        api.manage(new_manage_dest, **kw)

        # assert changes
        self.assertEqual(open(new_manage_dest).read(), MANAGE_CONTENTS)
        self.assertEqual(open(os.path.join(new_repo_dest, 'manage.py')).read(), MANAGE_CONTENTS)
        self.assertEqual(open(os.path.join(new_repo_dest, 'README')).read(), README_CONTENTS)
        self.assertEqual(open(os.path.join(new_repo_dest, 'versions/001_test.py')).read(), SCRIPT_FILE_CONTENTS)
        self.assertEqual(open(os.path.join(new_repo_dest, 'versions/002_foo_postgres_downgrade.sql')).read(), SCRIPT_FILE_CONTENTS)
        self.assertEqual(open(os.path.join(new_repo_dest, 'versions/002_foo_postgres_upgrade.sql')).read(), SCRIPT_FILE_CONTENTS)
