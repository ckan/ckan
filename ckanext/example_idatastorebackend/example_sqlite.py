# -*- coding: utf-8 -*-

import logging
from sqlalchemy import create_engine

from ckanext.datastore.backend import DatastoreBackend

log = logging.getLogger(__name__)


class DatastoreExampleSqliteBackend(DatastoreBackend):

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if not self._engine:
            self._engine = create_engine(self.write_url)
        return self._engine

    def _insert_records(self, table, records):
        if len(records):
            for record in records:
                self._get_engine().execute(
                    u'INSERT INTO "{0}"({1}) VALUES({2})'.format(
                        table,
                        u', '.join(record.keys()),
                        u', '.join(['?'] * len(record.keys()))
                    ),
                    record.values()
                )
            pass

    def configure(self, config):
        self.write_url = config.get(
            u'ckan.datastore.write_url'
        ).replace(u'example-', u'')

        return config

    def create(self, context, data_dict):
        columns = str(u', '.join(
            map(lambda e: e['id'] + u' text', data_dict['fields'])))
        engine = self._get_engine()
        engine.execute(
            u' CREATE TABLE IF NOT EXISTS "{name}"({columns});'.format(
                name=data_dict['resource_id'],
                columns=columns
            ))
        self._insert_records(data_dict['resource_id'], data_dict['records'])
        return data_dict

    def upsert(self, context, data_dict):
        raise NotImplementedError()

    def delete(self, context, data_dict):
        engine = self._get_engine()
        engine.execute(u'DROP TABLE IF EXISTS "{0}"'.format(
            data_dict['resource_id']
        ))
        return data_dict

    def search(self, context, data_dict):
        engine = self._get_engine()
        result = engine.execute(u'SELECT * FROM "{0}" LIMIT {1}'.format(
            data_dict['resource_id'],
            data_dict.get(u'limit', 10)
        ))

        data_dict['records'] = map(dict, result.fetchall())
        data_dict['total'] = len(data_dict['records'])

        fields_info = []
        for name, type in self.resource_fields(
                data_dict['resource_id'])['schema'].items():
            fields_info.append({
                u'type': type,
                u'id': name
            })
        data_dict['fields'] = fields_info
        return data_dict

    def search_sql(self, context, data_dict):
        raise NotImplementedError()

    def make_private(self, context, data_dict):
        pass

    def make_public(self, context, data_dict):
        pass

    def resource_exists(self, id):
        return self._get_engine().execute(
            u'''
            select name from sqlite_master
            where type = "table" and name = "{0}"'''.format(
                id)
        ).fetchone()

    def resource_fields(self, id):
        engine = self._get_engine()
        info = engine.execute(
            u'PRAGMA table_info("{0}")'.format(id)).fetchall()

        schema = {}
        for col in info:
            schema[col.name] = col.type
        return {u'schema': schema, u'meta': {}}

    def resource_id_from_alias(self, alias):
        if self.resource_exists(alias):
            return True, alias
        return False, alias

    def get_all_ids(self):
        return map(lambda t: t.name, self._get_engine().execute(
            u'''
            select name from sqlite_master
            where type = "table"'''
        ).fetchall())
