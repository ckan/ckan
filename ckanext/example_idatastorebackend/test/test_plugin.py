# encoding: utf-8


from unittest.mock import patch, Mock
import pytest
import sqlalchemy as sa
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
@pytest.mark.usefixtures(u"with_plugins", u"non_clean_db")
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

    @pytest.mark.usefixtures("with_request_context")
    @pytest.mark.ckan_config(u"ckan.datastore.write_url", u"sqlite://x")
    @pytest.mark.ckan_config(u"ckan.datastore.read_url", u"sqlite://x")
    @patch(class_to_patch + u".execute")
    def test_backend_functionality(self, execute):
        fetchall = execute().fetchall
        execute.reset_mock()

        COLUMN = "a;\"\' x"
        DatastoreExampleSqliteBackend.resource_fields = Mock(
            return_value={u"meta": {}, u"schema": {COLUMN: u"text"}}
        )
        records = [
            {COLUMN: u"x"},
            {COLUMN: u"y"},
            {COLUMN: u"z"},
        ]
        DatastoreBackend.set_active_backend(config)
        res = factories.Resource(url_type=u"datastore")
        helpers.call_action(
            u"datastore_create",
            resource_id=res["id"],
            fields=[{u"id": COLUMN}],
            records=records,
        )
        # check, create and 3 inserts
        assert 4 == execute.call_count
        insert_query = sa.insert(sa.table(
            res["id"], sa.column(COLUMN)
        ))

        call_args = [
            str(call.args[0])
            for call in execute.call_args_list
        ]
        assert call_args == [
            'CREATE TABLE IF NOT EXISTS "{}"({} text);'.format(
                res["id"],
                sa.column(COLUMN)
            ),
            str(insert_query.values({COLUMN: "x"})),
            str(insert_query.values({COLUMN: "y"})),
            str(insert_query.values({COLUMN: "z"})),
        ]

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
        c = u'''select name from sqlite_master where type = "table" and name = "{0}"'''.format(
            res["id"]
        )
        execute.assert_called_with(c)
