# encoding: utf-8

import unittest
import nose
import mock

from ckan.common import config

import ckan.tests.legacy as tests
import ckanext.datastore.backend.postgres as db
import ckanext.datastore.helpers as helpers
import ckanext.datastore.plugin as plugin
import ckanext.datastore.backend.postgres as backend

postgres_backend = backend.DatastorePostgresqlBackend()
postgres_backend.configure(config)


class TestTypeGetters(unittest.TestCase):
    def test_is_valid_field_name(self):
        assert helpers.is_valid_field_name("foo")
        assert helpers.is_valid_field_name("foo bar")
        assert helpers.is_valid_field_name("42")
        assert not helpers.is_valid_field_name('foo"bar')
        assert not helpers.is_valid_field_name('"')
        assert helpers.is_valid_field_name("'")
        assert not helpers.is_valid_field_name("")
        assert helpers.is_valid_field_name("foo%bar")

    def test_is_valid_table_name(self):
        assert helpers.is_valid_table_name("foo")
        assert helpers.is_valid_table_name("foo bar")
        assert helpers.is_valid_table_name("42")
        assert not helpers.is_valid_table_name('foo"bar')
        assert not helpers.is_valid_table_name('"')
        assert helpers.is_valid_table_name("'")
        assert not helpers.is_valid_table_name("")
        assert not helpers.is_valid_table_name("foo%bar")

    def test_pg_version_check(self):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        engine = db._get_engine_from_url(config['sqlalchemy.url'])
        connection = engine.connect()
        assert db._pg_version_is_at_least(connection, '8.0')
        assert not db._pg_version_is_at_least(connection, '20.0')
