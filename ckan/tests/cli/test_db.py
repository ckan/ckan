# -*- coding: utf-8 -*-

import os
import pytest

import ckan.migration as migration
import ckanext.example_database_migrations.plugin as example_plugin

import ckan.model as model
import ckan.cli.db as db


@pytest.fixture
def remove_extra_tables():
    # `clean_db` just removes data leaving tables intact. Thus we have to
    # downgrade database because we don't need those extra tables in the
    # following tests.
    yield
    db._run_migrations(u'example_database_migrations', None, False)


@pytest.mark.ckan_config("ckan.plugins", "example_database_migrations")
@pytest.mark.usefixtures("with_plugins", "non_clean_db", "remove_extra_tables")
class TestMigrations:

    def test_path_to_alembic_config(self):
        """Every plugins stores its migration inside separate folder.
        """
        config = db._resolve_alembic_config(None)
        assert config == os.path.join(
            os.path.dirname(migration.__file__), "alembic.ini")

        config = db._resolve_alembic_config("example_database_migrations")
        assert config == os.path.join(
            os.path.dirname(example_plugin.__file__),
            "migration/example_database_migrations/alembic.ini")

    def test_current_migration_version(self):
        """CKAN migration applied because of clean_db fixture.

        Migrations from plugins are not applied automatically.
        """
        version = db.current_revision(None)
        assert version.endswith("(head)")

        version = db.current_revision("example_database_migrations")
        assert version == "base"

    def check_upgrade(self, has_x, has_y, expected_version):
        has_table = model.Session.bind.has_table
        assert has_table("example_database_migrations_x") is has_x
        assert has_table("example_database_migrations_y") is has_y
        version = db.current_revision("example_database_migrations")
        assert version == expected_version

    def test_upgrade_database(self):
        self.check_upgrade(False, False, "base")

        # core migrations do not change plgugin's state
        db._run_migrations(None, None, True)
        self.check_upgrade(False, False, "base")

        # All migrations applied by default
        db._run_migrations(u'example_database_migrations', None, True)
        self.check_upgrade(True, True, "728663ebe30e (head)")

        # All migrations applied by default
        db._run_migrations(u'example_database_migrations', None, False)
        self.check_upgrade(False, False, "base")

        # Migrations can be applied one after another
        db._run_migrations(
            u'example_database_migrations', version="+1", forward=True)
        self.check_upgrade(True, False, "4f59069f433e")

        db._run_migrations(
            u'example_database_migrations', version="+1", forward=True)
        self.check_upgrade(True, True, "728663ebe30e (head)")

        # the same is true for downgrade
        db._run_migrations(
            u'example_database_migrations', version="-1", forward=False)
        self.check_upgrade(True, False, "4f59069f433e")

        db._run_migrations(
            u'example_database_migrations', version="-1", forward=False)
        self.check_upgrade(False, False, "base")

    def test_pending_list(self):
        db._run_migrations(u'example_database_migrations', None, False)

        assert db._get_pending_plugins() == {"example_database_migrations": 2}
        db._run_migrations(
            u'example_database_migrations', version="+1", forward=True)
        assert db._get_pending_plugins() == {"example_database_migrations": 1}
        db._run_migrations(u'example_database_migrations')
        assert db._get_pending_plugins() == {}
