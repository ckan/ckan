#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,shutil

from migrate.tests import fixture
from migrate.versioning.schema import *
from migrate.versioning import script


class TestRunChangeset(fixture.Pathed,fixture.DB):
    level=fixture.DB.CONNECT
    def _setup(self, url):
        super(TestRunChangeset, self)._setup(url)
        Repository.clear()
        self.path_repos=self.tmp_repos()
        # Create repository, script
        Repository.create(self.path_repos,'repository_name')

    @fixture.usedb()
    def test_changeset_run(self):
        """Running a changeset against a repository gives expected results"""
        repos=Repository(self.path_repos)
        for i in range(10):
            repos.create_script('')
        try:
            ControlledSchema(self.engine,repos).drop()
        except:
            pass
        db=ControlledSchema.create(self.engine,repos)

        # Scripts are empty; we'll check version # correctness.
        # (Correct application of their content is checked elsewhere)
        self.assertEqual(db.version,0)
        db.upgrade(1)
        self.assertEqual(db.version,1)
        db.upgrade(5)
        self.assertEqual(db.version,5)
        db.upgrade(5)
        self.assertEqual(db.version,5)
        db.upgrade(None) # Latest is implied
        self.assertEqual(db.version,10)
        self.assertRaises(Exception,db.upgrade,11)
        self.assertEqual(db.version,10)
        db.upgrade(9)
        self.assertEqual(db.version,9)
        db.upgrade(0)
        self.assertEqual(db.version,0)
        self.assertRaises(Exception,db.upgrade,-1)
        self.assertEqual(db.version,0)
        #changeset = repos.changeset(self.url,0)
        db.drop()
