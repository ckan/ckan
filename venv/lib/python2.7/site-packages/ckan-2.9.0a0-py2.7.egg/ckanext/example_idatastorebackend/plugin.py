# encoding: utf-8

from ckan import plugins
from ckanext.datastore.interfaces import IDatastoreBackend
from ckanext.example_idatastorebackend.example_sqlite import (
    DatastoreExampleSqliteBackend
)


class ExampleIDatastoreBackendPlugin(plugins.SingletonPlugin):
    plugins.implements(IDatastoreBackend)

    def register_backends(self):
        return {
            u'sqlite': DatastoreExampleSqliteBackend
        }
