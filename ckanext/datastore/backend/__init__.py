# -*- coding: utf-8 -*-

import re
import logging

import ckan.plugins as plugins
from ckan.common import config
from ckanext.datastore.interfaces import IDatastoreBackend

log = logging.getLogger(__name__)


def get_all_resources_ids_in_datastore():
    DatastoreBackend.register_backends()
    DatastoreBackend.set_active_backend(config)
    backend = DatastoreBackend.get_active_backend()
    backend.configure(config)
    return backend.get_all_ids()


def _parse_sort_clause(clause, fields_types):
    clause_match = re.match(u'^(.+?)( +(asc|desc) *)?$', clause, re.I)

    if not clause_match:
        return False

    field = clause_match.group(1)
    if field[0] == field[-1] == u'"':
        field = field[1:-1]
    sort = (clause_match.group(3) or u'asc').lower()

    if field not in fields_types:
        return False

    return field, sort


class DatastoreException(Exception):
    pass


class InvalidDataError(Exception):
    """Exception that's raised if you try to add invalid data to the datastore.

    For example if you have a column with type "numeric" and then you try to
    add a non-numeric value like "foo" to it, this exception should be raised.

    """
    pass


class DatastoreBackend:

    _backends = {}
    _active_backend = None

    @classmethod
    def register_backends(cls):
        for plugin in plugins.PluginImplementations(IDatastoreBackend):
            cls._backends.update(plugin.register_backends())

    @classmethod
    def set_active_backend(cls, config):
        schema = config.get('ckan.datastore.write_url').split(':')[0]
        cls._active_backend = cls._backends[schema]()

    @classmethod
    def get_active_backend(cls):
        return cls._active_backend

    def configure(self, config):
        return config

    def create(self, context, data_dict):
        raise NotImplementedError()

    def upsert(self, context, data_dict):
        raise NotImplementedError()

    def delete(self, context, data_dict):
        raise NotImplementedError()

    def search(self, context, data_dict):
        raise NotImplementedError()

    def search_sql(self, context, data_dict):
        raise NotImplementedError()

    def make_private(self, context, data_dict):
        raise NotImplementedError()

    def make_public(self, context, data_dict):
        raise NotImplementedError()

    def resource_exists(self, id):
        raise NotImplementedError()

    def resource_fields(self, id):
        raise NotImplementedError()

    def resource_info(self, id):
        raise NotImplementedError()

    def resource_id_from_alias(self, alias):
        raise NotImplementedError()

    def get_all_ids(self):
        raise NotImplementedError()
