import unittest
import pylons
import nose
import mock

from pylons import config

import ckan.tests as tests
import ckanext.datastore.db as db


class TestTypeGetters(unittest.TestCase):
    def test_list(self):
        assert db._get_list(None) is None
        assert db._get_list([]) == []
        assert db._get_list('') == []
        assert db._get_list('foo') == ['foo']
        assert db._get_list('foo, bar') == ['foo', 'bar']
        assert db._get_list('foo_"bar, baz') == ['foo_"bar', 'baz']
        assert db._get_list('"foo", "bar"') == ['foo', 'bar']
        assert db._get_list(u'foo, bar') == ['foo', 'bar']
        assert db._get_list(['foo', 'bar']) == ['foo', 'bar']
        assert db._get_list([u'foo', u'bar']) == ['foo', 'bar']
        assert db._get_list(['foo', ['bar', 'baz']]) == ['foo', ['bar', 'baz']]

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

    def _is_legacy_mode(self, config):

        from ckanext.datastore.plugin import _is_legacy_mode
        return _is_legacy_mode(config)

    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_legacy_mode_set_if_no_read_url_and_pg_9(self, pgv):

        pgv.return_value = True

        test_config = {
            'ckan.datastore.write_url': config['ckan.datastore.write_url'],
        }

        assert self._is_legacy_mode(test_config)

    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_legacy_mode_set_if_no_read_url_and_pg_8(self, pgv):

        pgv.return_value = False

        test_config = {
            'ckan.datastore.write_url': config['ckan.datastore.write_url'],
        }

        assert self._is_legacy_mode(test_config)

    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_legacy_mode_set_if_read_url_and_pg_8(self, pgv):

        pgv.return_value = False

        test_config = {
            'ckan.datastore.write_url': config['ckan.datastore.write_url'],
            'ckan.datastore.read_url': 'some_test_read_url',
        }

        assert self._is_legacy_mode(test_config)

    @mock.patch('ckanext.datastore.db._pg_version_is_at_least')
    def test_legacy_mode_not_set_if_read_url_and_pg_9(self, pgv):

        pgv.return_value = True

        test_config = {
            'ckan.datastore.write_url': config['ckan.datastore.write_url'],
            'ckan.datastore.read_url': 'some_test_read_url',
        }

        assert not self._is_legacy_mode(test_config)
