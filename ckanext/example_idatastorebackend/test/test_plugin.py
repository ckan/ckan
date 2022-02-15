# encoding: utf-8


from unittest.mock import patch, Mock, call
import pytest

from ckan.common import config
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckanext.datastore.backend import DatastoreBackend
from ckanext.datastore.backend.postgres import DatastorePostgresqlBackend
from ckanext.example_idatastorebackend.example_sqlite import (
    DatastoreExampleSqliteBackend,
)

class_to_patch = (
    u"ckanext.example_idatastorebackend."
    "example_sqlite.DatastoreExampleSqliteBackend"
)


@pytest.mark.ckan_config(u"ckan.plugins",
                         u"example_idatastorebackend datastore")
@pytest.mark.usefixtures(u"with_plugins", u"non_clean_db", u"with_request_context")
class TestExampleIDatastoreBackendPlugin():

    def test_backends_correctly_registered(self):
        DatastoreBackend.register_backends()
        assert u"sqlite" in DatastoreBackend._backends
        assert u"postgresql" in DatastoreBackend._backends

    def test_postgres_backend_with_standard_config(self):
        assert isinstance(
            DatastoreBackend.get_active_backend(), DatastorePostgresqlBackend
        )

    def test_inconsistent_engines_for_read_and_write(self):
        with helpers.changed_config(
            u"ckan.datastore.write_url", u"sqlite://x"
        ):
            with pytest.raises(AssertionError):
                DatastoreBackend.set_active_backend(config)
        with helpers.changed_config(u"ckan.datastore.read_url", u"sqlite://x"):
            with pytest.raises(AssertionError):
                DatastoreBackend.set_active_backend(config)

    @pytest.mark.ckan_config(u"ckan.datastore.write_url", u"sqlite://x")
    @pytest.mark.ckan_config(u"ckan.datastore.read_url", u"sqlite://x")
    def test_sqlite_engine(self):
        DatastoreBackend.set_active_backend(config)
        assert isinstance(
            DatastoreBackend.get_active_backend(),
            DatastoreExampleSqliteBackend,
        )

    @pytest.mark.ckan_config(u"ckan.datastore.write_url", u"sqlite://x")
    @pytest.mark.ckan_config(u"ckan.datastore.read_url", u"sqlite://x")
    @patch(class_to_patch + u"._get_engine")
    def test_backend_functionality(self, get_engine):
        engine = get_engine()
        execute = engine.execute
        fetchall = execute().fetchall
        execute.reset_mock()

        DatastoreExampleSqliteBackend.resource_fields = Mock(
            return_value={u"meta": {}, u"schema": {u"a": u"text"}}
        )
        records = [
            {u"a": u"x"},
            {u"a": u"y"},
            {u"a": u"z"},
        ]
        DatastoreBackend.set_active_backend(config)
        res = factories.Resource(url_type=u"datastore")
        helpers.call_action(
            u"datastore_create",
            resource_id=res["id"],
            fields=[{u"id": u"a"}],
            records=records,
        )
        # check, create and 3 inserts
        assert 4 == execute.call_count
        insert_query = u'INSERT INTO "{0}"(a) VALUES(?)'.format(res["id"])
        execute.assert_has_calls(
            [
                call(
                    u' CREATE TABLE IF NOT EXISTS "{0}"(a text);'.format(
                        res["id"]
                    )
                ),
                call(insert_query, ["x"]),
                call(insert_query, ["y"]),
                call(insert_query, ["z"]),
            ]
        )

        execute.reset_mock()
        fetchall.return_value = records
        helpers.call_action(u"datastore_search", resource_id=res["id"])
        execute.assert_called_with(
            u'SELECT * FROM "{0}" LIMIT 100'.format(res["id"])
        )

        execute.reset_mock()
        helpers.call_action(u"datastore_delete", resource_id=res["id"])
        # check delete
        execute.assert_called_with(
            u'DROP TABLE IF EXISTS "{0}"'.format(res["id"])
        )

        execute.reset_mock()
        helpers.call_action(u"datastore_info", id=res["id"])
        # check
        c = u'''
            select name from sqlite_master
            where type = "table" and name = "{0}"'''.format(
            res["id"]
        )
        execute.assert_called_with(c)
