#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

from migrate import exceptions
from migrate.versioning.repository import *
from migrate.versioning.script import *

from migrate.tests import fixture
from datetime import datetime


class TestRepository(fixture.Pathed):
    def test_create(self):
        """Repositories are created successfully"""
        path = self.tmp_repos()
        name = 'repository_name'

        # Creating a repository that doesn't exist should succeed
        repo = Repository.create(path, name)
        config_path = repo.config.path
        manage_path = os.path.join(repo.path, 'manage.py')
        self.assertTrue(repo)

        # Files should actually be created
        self.assertTrue(os.path.exists(path))
        self.assertTrue(os.path.exists(config_path))
        self.assertTrue(os.path.exists(manage_path))

        # Can't create it again: it already exists
        self.assertRaises(exceptions.PathFoundError, Repository.create, path, name)
        return path

    def test_load(self):
        """We should be able to load information about an existing repository"""
        # Create a repository to load
        path = self.test_create()
        repos = Repository(path)

        self.assertTrue(repos)
        self.assertTrue(repos.config)
        self.assertTrue(repos.config.get('db_settings', 'version_table'))

        # version_table's default isn't none
        self.assertNotEqual(repos.config.get('db_settings', 'version_table'), 'None')

    def test_load_notfound(self):
        """Nonexistant repositories shouldn't be loaded"""
        path = self.tmp_repos()
        self.assertTrue(not os.path.exists(path))
        self.assertRaises(exceptions.InvalidRepositoryError, Repository, path)

    def test_load_invalid(self):
        """Invalid repos shouldn't be loaded"""
        # Here, invalid=empty directory. There may be other conditions too,
        # but we shouldn't need to test all of them
        path = self.tmp_repos()
        os.mkdir(path)
        self.assertRaises(exceptions.InvalidRepositoryError, Repository, path)


class TestVersionedRepository(fixture.Pathed):
    """Tests on an existing repository with a single python script"""

    def setUp(self):
        super(TestVersionedRepository, self).setUp()
        Repository.clear()
        self.path_repos = self.tmp_repos()
        Repository.create(self.path_repos, 'repository_name')

    def test_version(self):
        """We should correctly detect the version of a repository"""
        repos = Repository(self.path_repos)

        # Get latest version, or detect if a specified version exists
        self.assertEqual(repos.latest, 0)
        # repos.latest isn't an integer, but a VerNum
        # (so we can't just assume the following tests are correct)
        self.assertTrue(repos.latest >= 0)
        self.assertTrue(repos.latest < 1)

        # Create a script and test again
        repos.create_script('')
        self.assertEqual(repos.latest, 1)
        self.assertTrue(repos.latest >= 0)
        self.assertTrue(repos.latest >= 1)
        self.assertTrue(repos.latest < 2)

        # Create a new script and test again
        repos.create_script('')
        self.assertEqual(repos.latest, 2)
        self.assertTrue(repos.latest >= 0)
        self.assertTrue(repos.latest >= 1)
        self.assertTrue(repos.latest >= 2)
        self.assertTrue(repos.latest < 3)


    def test_timestmap_numbering_version(self):
        repos = Repository(self.path_repos)
        repos.config.set('db_settings', 'use_timestamp_numbering', 'True')

        # Get latest version, or detect if a specified version exists
        self.assertEqual(repos.latest, 0)
        # repos.latest isn't an integer, but a VerNum
        # (so we can't just assume the following tests are correct)
        self.assertTrue(repos.latest >= 0)
        self.assertTrue(repos.latest < 1)

        # Create a script and test again
        now = int(datetime.utcnow().strftime('%Y%m%d%H%M%S'))
        repos.create_script('')
        self.assertEqual(repos.latest, now)

    def test_source(self):
        """Get a script object by version number and view its source"""
        # Load repository and commit script
        repo = Repository(self.path_repos)
        repo.create_script('')
        repo.create_script_sql('postgres', 'foo bar')

        # Source is valid: script must have an upgrade function
        # (not a very thorough test, but should be plenty)
        source = repo.version(1).script().source()
        self.assertTrue(source.find('def upgrade') >= 0)

        import pprint; pprint.pprint(repo.version(2).sql)
        source = repo.version(2).script('postgres', 'upgrade').source()
        self.assertEqual(source.strip(), '')

    def test_latestversion(self):
        """Repository.version() (no params) returns the latest version"""
        repos = Repository(self.path_repos)
        repos.create_script('')
        self.assertTrue(repos.version(repos.latest) is repos.version())
        self.assertTrue(repos.version() is not None)

    def test_changeset(self):
        """Repositories can create changesets properly"""
        # Create a nonzero-version repository of empty scripts
        repos = Repository(self.path_repos)
        for i in range(10):
            repos.create_script('')

        def check_changeset(params, length):
            """Creates and verifies a changeset"""
            changeset = repos.changeset('postgres', *params)
            self.assertEqual(len(changeset), length)
            self.assertTrue(isinstance(changeset, Changeset))
            uniq = list()
            # Changesets are iterable
            for version, change in changeset:
                self.assertTrue(isinstance(change, BaseScript))
                # Changes aren't identical
                self.assertTrue(id(change) not in uniq)
                uniq.append(id(change))
            return changeset

        # Upgrade to a specified version...
        cs = check_changeset((0, 10), 10)
        self.assertEqual(cs.keys().pop(0),0 ) # 0 -> 1: index is starting version
        self.assertEqual(cs.keys().pop(), 9) # 9 -> 10: index is starting version
        self.assertEqual(cs.start, 0) # starting version
        self.assertEqual(cs.end, 10) # ending version
        check_changeset((0, 1), 1)
        check_changeset((0, 5), 5)
        check_changeset((0, 0), 0)
        check_changeset((5, 5), 0)
        check_changeset((10, 10), 0)
        check_changeset((5, 10), 5)

        # Can't request a changeset of higher version than this repository
        self.assertRaises(Exception, repos.changeset, 'postgres', 5, 11)
        self.assertRaises(Exception, repos.changeset, 'postgres', -1, 5)

        # Upgrade to the latest version...
        cs = check_changeset((0,), 10)
        self.assertEqual(cs.keys().pop(0), 0)
        self.assertEqual(cs.keys().pop(), 9)
        self.assertEqual(cs.start, 0)
        self.assertEqual(cs.end, 10)
        check_changeset((1,), 9)
        check_changeset((5,), 5)
        check_changeset((9,), 1)
        check_changeset((10,), 0)

        # run changes
        cs.run('postgres', 'upgrade')

        # Can't request a changeset of higher/lower version than this repository
        self.assertRaises(Exception, repos.changeset, 'postgres', 11)
        self.assertRaises(Exception, repos.changeset, 'postgres', -1)

        # Downgrade
        cs = check_changeset((10, 0),10)
        self.assertEqual(cs.keys().pop(0), 10) # 10 -> 9
        self.assertEqual(cs.keys().pop(), 1)    # 1 -> 0
        self.assertEqual(cs.start, 10)
        self.assertEqual(cs.end, 0)
        check_changeset((10, 5), 5)
        check_changeset((5, 0), 5)

    def test_many_versions(self):
        """Test what happens when lots of versions are created"""
        repos = Repository(self.path_repos)
        for i in range(1001):
            repos.create_script('')

        # since we normally create 3 digit ones, let's see if we blow up
        self.assertTrue(os.path.exists('%s/versions/1000.py' % self.path_repos))
        self.assertTrue(os.path.exists('%s/versions/1001.py' % self.path_repos))


# TODO: test manage file
# TODO: test changeset
