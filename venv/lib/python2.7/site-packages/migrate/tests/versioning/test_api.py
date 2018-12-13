#!/usr/bin/python
# -*- coding: utf-8 -*-

import six

from migrate.exceptions import *
from migrate.versioning import api

from migrate.tests.fixture.pathed import *
from migrate.tests.fixture import models
from migrate.tests import fixture


class TestAPI(Pathed):

    def test_help(self):
        self.assertTrue(isinstance(api.help('help'), six.string_types))
        self.assertRaises(UsageError, api.help)
        self.assertRaises(UsageError, api.help, 'foobar')
        self.assertTrue(isinstance(api.help('create'), str))

        # test that all commands return some text
        for cmd in api.__all__:
            content = api.help(cmd)
            self.assertTrue(content)

    def test_create(self):
        tmprepo = self.tmp_repos()
        api.create(tmprepo, 'temp')

        # repository already exists
        self.assertRaises(KnownError, api.create, tmprepo, 'temp')

    def test_script(self):
        repo = self.tmp_repos()
        api.create(repo, 'temp')
        api.script('first version', repo)

    def test_script_sql(self):
        repo = self.tmp_repos()
        api.create(repo, 'temp')
        api.script_sql('postgres', 'desc', repo)

    def test_version(self):
        repo = self.tmp_repos()
        api.create(repo, 'temp')
        api.version(repo)

    def test_version_control(self):
        repo = self.tmp_repos()
        api.create(repo, 'temp')
        api.version_control('sqlite:///', repo)
        api.version_control('sqlite:///', six.text_type(repo))

    def test_source(self):
        repo = self.tmp_repos()
        api.create(repo, 'temp')
        api.script('first version', repo)
        api.script_sql('default', 'desc', repo)

        # no repository
        self.assertRaises(UsageError, api.source, 1)

        # stdout
        out = api.source(1, dest=None, repository=repo)
        self.assertTrue(out)

        # file
        out = api.source(1, dest=self.tmp_repos(), repository=repo)
        self.assertFalse(out)

    def test_manage(self):
        output = api.manage(os.path.join(self.temp_usable_dir, 'manage.py'))


class TestSchemaAPI(fixture.DB, Pathed):

    def _setup(self, url):
        super(TestSchemaAPI, self)._setup(url)
        self.repo = self.tmp_repos()
        api.create(self.repo, 'temp')
        self.schema = api.version_control(url, self.repo)

    def _teardown(self):
        self.schema = api.drop_version_control(self.url, self.repo)
        super(TestSchemaAPI, self)._teardown()

    @fixture.usedb()
    def test_workflow(self):
        self.assertEqual(api.db_version(self.url, self.repo), 0)
        api.script('First Version', self.repo)
        self.assertEqual(api.db_version(self.url, self.repo), 0)
        api.upgrade(self.url, self.repo, 1)
        self.assertEqual(api.db_version(self.url, self.repo), 1)
        api.downgrade(self.url, self.repo, 0)
        self.assertEqual(api.db_version(self.url, self.repo), 0)
        api.test(self.url, self.repo)
        self.assertEqual(api.db_version(self.url, self.repo), 0)

        # preview
        # TODO: test output
        out = api.upgrade(self.url, self.repo, preview_py=True)
        out = api.upgrade(self.url, self.repo, preview_sql=True)

        api.upgrade(self.url, self.repo, 1)
        api.script_sql('default', 'desc', self.repo)
        self.assertRaises(UsageError, api.upgrade, self.url, self.repo, 2, preview_py=True)
        out = api.upgrade(self.url, self.repo, 2, preview_sql=True)

        # cant upgrade to version 1, already at version 1
        self.assertEqual(api.db_version(self.url, self.repo), 1)
        self.assertRaises(KnownError, api.upgrade, self.url, self.repo, 0)

    @fixture.usedb()
    def test_compare_model_to_db(self):
        diff = api.compare_model_to_db(self.url, self.repo, models.meta)

    @fixture.usedb()
    def test_create_model(self):
        model = api.create_model(self.url, self.repo)

    @fixture.usedb()
    def test_make_update_script_for_model(self):
        model = api.make_update_script_for_model(self.url, self.repo, models.meta_old_rundiffs, models.meta_rundiffs)

    @fixture.usedb()
    def test_update_db_from_model(self):
        model = api.update_db_from_model(self.url, self.repo, models.meta_rundiffs)
