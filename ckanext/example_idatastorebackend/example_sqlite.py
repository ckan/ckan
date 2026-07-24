# type: ignore
from __future__ import annotations

import logging
from typing import Any
import sqlalchemy as sa

from ckanext.datastore.backend import DatastoreBackend

log = logging.getLogger(__name__)


class DatastoreExampleSqliteBackend(DatastoreBackend):

    def __init__(self):
        self._engine = None

    def execute(self, sql: str, params: dict[str, Any] | None = None):
        with self._get_engine().begin() as conn:
            return conn.execute(sa.text(sql), params)

    def _get_engine(self):
        if not self._engine:
            self._engine = sa.create_engine(self.write_url)
        return self._engine

    def _insert_records(self, table, records):
        if len(records):
            for record in records:
                sql = sa.insert(
                    sa.table(table, *map(sa.column, record))
                ).values(record)
                self.execute(sql)

    def configure(self, config):
        self.write_url = config.get(
            u'ckan.datastore.write_url'
        ).replace(u'example-', u'')

        return config

    def create(self, context, data_dict, plugin_data):
        columns = str(u', '.join(
            [str(sa.column(e['id'])) + " text" for e in data_dict['fields']]))

        self.execute(sa.text(
            'CREATE TABLE IF NOT EXISTS "{name}"({columns});'.format(
                name=sa.table(data_dict['resource_id']),
                columns=columns
            )
        ))
        self._insert_records(data_dict['resource_id'], data_dict['records'])
        return data_dict

    def upsert(self, context, data_dict):
        raise NotImplementedError()

    def delete(self, context, data_dict):
        self.execute('DROP TABLE IF EXISTS "{0}"'.format(
            data_dict['resource_id']
        ))
        return data_dict

    def search(self, context, data_dict):
        result = self.execute('SELECT * FROM "{0}" LIMIT {1}'.format(
            data_dict['resource_id'],
            data_dict.get(u'limit', 10)
        ))

        data_dict['records'] = list(map(dict, result.fetchall()))
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
        return self.execute(
            'select name from sqlite_master where ' +
            f'type = "table" and name = "{id}"'
        ).fetchone()

    def resource_fields(self, id):
        info = self.execute(
            'PRAGMA table_info("{0}")'.format(id)
        ).fetchall()

        schema = {}
        for col in info:
            schema[col.name] = col.type
        return {u'schema': schema, u'meta': {}}

    def resource_id_from_alias(self, alias):
        if self.resource_exists(alias):
            return True, alias
        return False, alias

    def get_all_ids(self):
        return [t.name for t in self.execute(
            '''select name from sqlite_master
            where type = "table"'''
        ).fetchall()]
