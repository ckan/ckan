# encoding: utf-8


from mock import patch, Mock, call
from nose.tools import (
    assert_equal,
    assert_in,
    assert_is_instance,
    assert_raises
)

import ckan.plugins as plugins
from ckan.common import config
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckanext.datastore.backend import DatastoreBackend
from ckanext.datastore.backend.postgres import DatastorePostgresqlBackend
from ckanext.example_idatastorebackend.example_sqlite import (
    DatastoreExampleSqliteBackend
)

class_to_patch = (
    u'ckanext.example_idatastorebackend.'
    'example_sqlite.DatastoreExampleSqliteBackend'
)


class ExampleIDatastoreBackendPlugin(helpers.FunctionalTestBase):

    def setup(self):
        super(TestExampleIDatastoreBackendPlugin, self).setup()
        plugins.load(u'datastore')
        plugins.load(u'example_idatastorebackend')

    def teardown(self):
        plugins.unload(u'example_idatastorebackend')
        plugins.unload(u'datastore')

    def test_backends_correctly_registered(self):
        DatastoreBackend.register_backends()
        assert_in(u'sqlite', DatastoreBackend._backends)
        assert_in(u'postgresql', DatastoreBackend._backends)

    def test_postgres_backend_with_standard_config(self):
        assert_is_instance(
            DatastoreBackend.get_active_backend(),
            DatastorePostgresqlBackend)

    def test_inconsistent_engines_for_read_and_write(self):
        with helpers.changed_config(u'ckan.datastore.write_url', u'sqlite://x'):
            assert_raises(
                AssertionError,
                DatastoreBackend.set_active_backend, config)
        with helpers.changed_config(u'ckan.datastore.read_url', u'sqlite://x'):
            assert_raises(
                AssertionError,
                DatastoreBackend.set_active_backend, config)

    @helpers.change_config(u'ckan.datastore.write_url', u'sqlite://x')
    @helpers.change_config(u'ckan.datastore.read_url', u'sqlite://x')
    def test_sqlite_engine(self):
        DatastoreBackend.set_active_backend(config)
        assert_is_instance(
            DatastoreBackend.get_active_backend(),
            DatastoreExampleSqliteBackend)

    @helpers.change_config(u'ckan.datastore.write_url', u'sqlite://x')
    @helpers.change_config(u'ckan.datastore.read_url', u'sqlite://x')
    @patch(class_to_patch + u'._get_engine')
    def test_backend_functionality(self, get_engine):
        engine = get_engine()
        execute = engine.execute
        fetchall = execute().fetchall
        execute.reset_mock()

        DatastoreExampleSqliteBackend.resource_fields = Mock(
            return_value={u'meta': {}, u'schema': {
                u'a': u'text'
            }}
        )
        records = [
            {u'a': u'x'}, {u'a': u'y'}, {u'a': u'z'},
        ]
        DatastoreBackend.set_active_backend(config)
        res = factories.Resource(url_type=u'datastore')
        helpers.call_action(
            u'datastore_create', resource_id=res['id'],
            fields=[
                {u'id': u'a'}
            ], records=records
        )
        # check, create and 3 inserts
        assert_equal(5, execute.call_count)
        insert_query = u'INSERT INTO "{0}"(a) VALUES(?)'.format(res['id'])
        execute.assert_has_calls(
            [
                call(u' CREATE TABLE IF NOT EXISTS "{0}"(a text);'.format(
                    res['id']
                )),
                call(insert_query, ['x']),
                call(insert_query, ['y']),
                call(insert_query, ['z'])
            ])

        execute.reset_mock()
        fetchall.return_value = records
        helpers.call_action(
            u'datastore_search', resource_id=res['id'])
        execute.assert_called_with(
            u'SELECT * FROM "{0}" LIMIT 10'.format(res['id'])
        )

        execute.reset_mock()
        helpers.call_action(
            u'datastore_delete', resource_id=res['id'])
        # check delete
        execute.assert_called_with(
            u'DROP TABLE IF EXISTS "{0}"'.format(res['id'])
        )

        execute.reset_mock()
        helpers.call_action(
            u'datastore_info', id=res['id'])
        # check
        c = u'''
            select name from sqlite_master
            where type = "table" and name = "{0}"'''.format(res['id'])
        execute.assert_called_with(c)
