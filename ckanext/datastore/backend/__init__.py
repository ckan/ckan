# -*- coding: utf-8 -*-

import re
import logging

import ckan.plugins as plugins

log = logging.getLogger(__name__)


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


class DatastoreBackend:

    _backends = {}

    @classmethod
    def register_backend(cls, backends_dict):
        cls._backends.update(backends_dict)

    @classmethod
    def get_active_backend(cls, config):
        schema = config.get('ckan.datastore.write_url').split(':')[0]
        return cls._backends[schema]()

    def configure(self, config):
        return config

    def create(self, context, data_dict):
        pass

    def upsert(self, context, data_dict):
        pass

    def delete(self, context, data_dict):
        pass

    def search(self, context, data_dict):
        pass

    def search_sql(self, context, data_dict):
        pass

    def resource_exists(self, id):
        pass

    def resource_fields(self, id):
        pass

    def resource_info(self, id):
        pass
