import unittest
import pylons
import nose
import mock

from pylons import config

import ckan.tests.legacy as tests
import ckanext.datastore.db as db
import ckanext.datastore.plugin as plugin


class TestTypeGetters(unittest.TestCase):
    def test_is_valid_field_name(self):
        assert db._is_valid_field_name("foo")
        assert db._is_valid_field_name("foo bar")
        assert db._is_valid_field_name("42")
        assert not db._is_valid_field_name('foo"bar')
        assert not db._is_valid_field_name('"')
        assert db._is_valid_field_name("'")
        assert not db._is_valid_field_name("")
        assert db._is_valid_field_name("foo%bar")

    def test_is_valid_table_name(self):
        assert db._is_valid_table_name("foo")
        assert db._is_valid_table_name("foo bar")
        assert db._is_valid_table_name("42")
        assert not db._is_valid_table_name('foo"bar')
        assert not db._is_valid_table_name('"')
        assert db._is_valid_table_name("'")
        assert not db._is_valid_table_name("")
        assert not db._is_valid_table_name("foo%bar")

    def test_pg_version_check(self):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        engine = db._get_engine(
            {'connection_url': pylons.config['sqlalchemy.url']})
        connection = engine.connect()
        assert db._pg_version_is_at_least(connection, '8.0')
        assert not db._pg_version_is_at_least(connection, '10.0')


class TestLegacyModeSetting():

    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_legacy_mode_set_if_no_read_url_and_pg_9(self, pgv):

        pgv.return_value = True

        test_config = {
            'ckan.datastore.write_url': config['ckan.datastore.write_url'],
        }

        assert plugin._is_legacy_mode(test_config)

    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_legacy_mode_set_if_no_read_url_and_pg_8(self, pgv):

        pgv.return_value = False

        test_config = {
            'ckan.datastore.write_url': config['ckan.datastore.write_url'],
        }

        assert plugin._is_legacy_mode(test_config)

    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_legacy_mode_set_if_read_url_and_pg_8(self, pgv):

        pgv.return_value = False

        test_config = {
            'ckan.datastore.write_url': config['ckan.datastore.write_url'],
            'ckan.datastore.read_url': 'some_test_read_url',
        }

        assert plugin._is_legacy_mode(test_config)

    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_legacy_mode_not_set_if_read_url_and_pg_9(self, pgv):

        pgv.return_value = True

        test_config = {
            'ckan.datastore.write_url': config['ckan.datastore.write_url'],
            'ckan.datastore.read_url': 'some_test_read_url',
        }

        assert not plugin._is_legacy_mode(test_config)
