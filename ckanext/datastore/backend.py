# -*- coding: utf-8 -*-

import re
import sys
import logging

import sqlalchemy.engine.url as sa_url

import ckan.model as model
import ckan.plugins.toolkit as toolkit
from ckan.common import config
import ckanext.datastore.db as db
import ckanext.datastore.helpers as datastore_helpers
from ckanext.datastore.helpers import literal_string

log = logging.getLogger(__name__)


def _is_legacy_mode(config):
    '''
        Decides if the DataStore should run on legacy mode

        Returns True if `ckan.datastore.read_url` is not set in the provided
        config object or CKAN is running on Postgres < 9.x
    '''
    write_url = config.get('ckan.datastore.write_url')

    engine = db._get_engine({'connection_url': write_url})
    connection = engine.connect()

    return (not config.get('ckan.datastore.read_url') or
            not db._pg_version_is_at_least(connection, '9.0'))


def _is_array_type(field_type):
    return field_type.startswith('_')


def _where(data_dict, fields_types):
    filters = data_dict.get('filters', {})
    clauses = []

    for field, value in filters.iteritems():
        if field not in fields_types:
            continue
        field_array_type = _is_array_type(fields_types[field])
        if isinstance(value, list) and not field_array_type:
            clause_str = (u'"{0}" in ({1})'.format(field,
                          ','.join(['%s'] * len(value))))
            clause = (clause_str,) + tuple(value)
        else:
            clause = (u'"{0}" = %s'.format(field), value)
        clauses.append(clause)

    # add full-text search where clause
    q = data_dict.get('q')
    if q:
        if isinstance(q, basestring):
            ts_query_alias = _ts_query_alias()
            clause_str = u'_full_text @@ {0}'.format(ts_query_alias)
            clauses.append((clause_str,))
        elif isinstance(q, dict):
            lang = _fts_lang(data_dict.get('lang'))
            for field, value in q.iteritems():
                if field not in fields_types:
                    continue
                query_field = _ts_query_alias(field)

                ftyp = fields_types[field]
                if not datastore_helpers.should_fts_index_field_type(ftyp):
                    clause_str = u'_full_text @@ {0}'.format(query_field)
                    clauses.append((clause_str,))

                clause_str = (u'to_tsvector({0}, cast("{1}" as text)) '
                              u'@@ {2}').format(literal_string(lang),
                                                field, query_field)
                clauses.append((clause_str,))

    return clauses


def _textsearch_query(data_dict):
    q = data_dict.get('q')
    lang = _fts_lang(data_dict.get('lang'))

    if not q:
        return '', ''

    statements = []
    rank_columns = []
    plain = data_dict.get('plain', True)
    if isinstance(q, basestring):
        query, rank = _build_query_and_rank_statements(
            lang, q, plain)
        statements.append(query)
        rank_columns.append(rank)
    elif isinstance(q, dict):
        for field, value in q.iteritems():
            query, rank = _build_query_and_rank_statements(
                lang, value, plain, field)
            statements.append(query)
            rank_columns.append(rank)

    statements_str = ', ' + ', '.join(statements)
    rank_columns_str = ', ' + ', '.join(rank_columns)
    return statements_str, rank_columns_str


def _build_query_and_rank_statements(lang, query, plain, field=None):
    query_alias = _ts_query_alias(field)
    rank_alias = _ts_rank_alias(field)
    lang_literal = literal_string(lang)
    query_literal = literal_string(query)
    if plain:
        statement = u"plainto_tsquery({lang_literal}, {literal}) {alias}"
    else:
        statement = u"to_tsquery({lang_literal}, {literal}) {alias}"
    statement = statement.format(
        lang_literal=lang_literal,
        literal=query_literal, alias=query_alias)
    if field is None:
        rank_field = '_full_text'
    else:
        rank_field = u'to_tsvector({lang_literal}, cast("{field}" as text))'
        rank_field = rank_field.format(lang_literal=lang_literal, field=field)
    rank_statement = u'ts_rank({rank_field}, {query_alias}, 32) AS {alias}'
    rank_statement = rank_statement.format(rank_field=rank_field,
                                           query_alias=query_alias,
                                           alias=rank_alias)
    return statement, rank_statement


def _fts_lang(lang=None):
    default_fts_lang = config.get('ckan.datastore.default_fts_lang')
    if default_fts_lang is None:
        default_fts_lang = u'english'
    return lang or default_fts_lang


def _ts_rank_alias(field=None):
    rank_alias = u'rank'
    if field:
        rank_alias += u' ' + field
    return u'"{0}"'.format(rank_alias)


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


def _sort(data_dict, fields_types):
    sort = data_dict.get('sort')
    if not sort:
        q = data_dict.get('q')
        if q:
            if isinstance(q, basestring):
                return [_ts_rank_alias()]
            elif isinstance(q, dict):
                return [_ts_rank_alias(field) for field in q
                        if field not in fields_types]
        else:
            return []

    clauses = datastore_helpers.get_list(sort, False)

    clause_parsed = []

    for clause in clauses:
        field, sort = _parse_sort_clause(clause, fields_types)
        clause_parsed.append(
            u'{0} {1}'.format(datastore_helpers.identifier(field), sort))

    return clause_parsed


def _ts_query_alias(field=None):
    query_alias = u'query'
    if field:
        query_alias += u' ' + field
    return u'"{0}"'.format(query_alias)


class DatastoreException(Exception):
    pass


class DatastoreBackend:
    def datastore_validate(self, context, data_dict, field_types):
        return data_dict

    def datastore_delete(self, context, data_dict, field_types, query_dict):
        return query_dict

    def datastore_search(self, context, data_dict, field_types, query_dict):
        return query_dict

    def is_legacy_mode(self, config):
        return False

    def configure_datastore(self, config):
        return config

    def advanced_search_enabled(self):
        return False


class DatastorePostgresqlBackend(DatastoreBackend):

    def _log_or_raise(self, message):
        if self.config.get('debug'):
            log.critical(message)
        else:
            raise DatastoreException(message)

    def _check_urls_and_permissions(self):
        # Make sure that the right permissions are set
        # so that no harmful queries can be made

        if self._same_ckan_and_datastore_db():
            self._log_or_raise(
                'CKAN and DataStore database cannot be the same.')

        # in legacy mode, the read and write url are the same (both write url)
        # consequently the same url check and and write privilege check
        # don't make sense
        if not self.legacy_mode:
            if self._same_read_and_write_url():
                self._log_or_raise('The write and read-only database '
                                   'connection urls are the same.')

            if not self._read_connection_has_correct_privileges():
                self._log_or_raise('The read-only user has write privileges.')

    def _is_read_only_database(self):
        ''' Returns True if no connection has CREATE privileges on the public
        schema. This is the case if replication is enabled.'''
        for url in [self.ckan_url, self.write_url, self.read_url]:
            connection = db._get_engine({'connection_url': url}).connect()
            try:
                sql = u"SELECT has_schema_privilege('public', 'CREATE')"
                is_writable = connection.execute(sql).first()[0]
            finally:
                connection.close()
            if is_writable:
                return False
        return True

    def _same_ckan_and_datastore_db(self):
        '''Returns True if the CKAN and DataStore db are the same'''
        return self._get_db_from_url(self.ckan_url) == self._get_db_from_url(
            self.read_url)

    def _get_db_from_url(self, url):
        db_url = sa_url.make_url(url)
        return db_url.host, db_url.port, db_url.database

    def _same_read_and_write_url(self):
        return self.write_url == self.read_url

    def _read_connection_has_correct_privileges(self):
        ''' Returns True if the right permissions are set for the read
        only user. A table is created by the write user to test the
        read only user.
        '''
        write_connection = db._get_engine(
            {'connection_url': self.write_url}).connect()
        read_connection_user = sa_url.make_url(self.read_url).username

        drop_foo_sql = u'DROP TABLE IF EXISTS _foo'

        write_connection.execute(drop_foo_sql)

        try:
            write_connection.execute(u'CREATE TEMP TABLE _foo ()')
            for privilege in ['INSERT', 'UPDATE', 'DELETE']:
                privilege_sql = u"SELECT has_table_privilege(%s, '_foo', %s)"
                have_privilege = write_connection.execute(
                    privilege_sql,
                    (read_connection_user, privilege)
                ).first()[0]
                if have_privilege:
                    return False
        finally:
            write_connection.execute(drop_foo_sql)
            write_connection.close()
        return True

    def advanced_search_enabled(self):
        return self.enable_sql_search

    def is_legacy_mode(self, config):
        return _is_legacy_mode(config)

    def configure_datastore(self, config):
        self.config = config
        self.legacy_mode = self.is_legacy_mode(config)
        # check for ckan.datastore.write_url and ckan.datastore.read_url
        if ('ckan.datastore.write_url' not in config):
            error_msg = 'ckan.datastore.write_url not found in config'
            raise DatastoreException(error_msg)

        # Check whether users have disabled datastore_search_sql
        self.enable_sql_search = toolkit.asbool(
            self.config.get('ckan.datastore.sqlsearch.enabled', True))

        # Check whether we are running one of the paster commands which means
        # that we should ignore the following tests.
        args = sys.argv
        if args[0].split('/')[-1] == 'paster' and 'datastore' in args[1:]:
            log.warn('Omitting permission checks because you are '
                     'running paster commands.')
            return

        self.ckan_url = self.config['sqlalchemy.url']
        self.write_url = self.config['ckan.datastore.write_url']
        if self.legacy_mode:
            self.read_url = self.write_url
            log.warn('Legacy mode active. '
                     'The sql search will not be available.')
        else:
            self.read_url = self.config['ckan.datastore.read_url']

        self.read_engine = db._get_engine(
            {'connection_url': self.read_url})
        if not model.engine_is_pg(self.read_engine):
            log.warn('We detected that you do not use a PostgreSQL '
                     'database. The DataStore will NOT work and DataStore '
                     'tests will be skipped.')
            return

        if self._is_read_only_database():
            log.warn('We detected that CKAN is running on a read '
                     'only database. Permission checks and the creation '
                     'of _table_metadata are skipped.')
        else:
            self._check_urls_and_permissions()

    def datastore_validate(self, context, data_dict, fields_types):
        column_names = fields_types.keys()
        fields = data_dict.get('fields')
        if fields:
            data_dict['fields'] = list(set(fields) - set(column_names))

        filters = data_dict.get('filters', {})
        for key in filters.keys():
            if key in fields_types:
                del filters[key]

        q = data_dict.get('q')
        if q:
            if isinstance(q, basestring):
                del data_dict['q']
            elif isinstance(q, dict):
                for key in q.keys():
                    if key in fields_types and isinstance(q[key], basestring):
                        del q[key]

        language = data_dict.get('language')
        if language:
            if isinstance(language, basestring):
                del data_dict['language']

        plain = data_dict.get('plain')
        if plain:
            if isinstance(plain, bool):
                del data_dict['plain']

        distinct = data_dict.get('distinct')
        if distinct:
            if isinstance(distinct, bool):
                del data_dict['distinct']

        sort_clauses = data_dict.get('sort')
        if sort_clauses:
            invalid_clauses = [c for c in sort_clauses
                               if not _parse_sort_clause(c, fields_types)]
            data_dict['sort'] = invalid_clauses

        limit = data_dict.get('limit')
        if limit:
            is_positive_int = datastore_helpers.validate_int(limit,
                                                             non_negative=True)
            is_all = isinstance(limit, basestring) and limit.lower() == 'all'
            if is_positive_int or is_all:
                del data_dict['limit']

        offset = data_dict.get('offset')
        if offset:
            is_positive_int = datastore_helpers.validate_int(offset,
                                                             non_negative=True)
            if is_positive_int:
                del data_dict['offset']

        return data_dict

    def datastore_delete(self, context, data_dict, fields_types, query_dict):
        query_dict['where'] += _where(data_dict, fields_types)
        return query_dict

    def datastore_search(self, context, data_dict, fields_types, query_dict):
        fields = data_dict.get('fields')

        if fields:
            field_ids = datastore_helpers.get_list(fields)
        else:
            field_ids = fields_types.keys()

        ts_query, rank_column = _textsearch_query(data_dict)
        limit = data_dict.get('limit', 100)
        offset = data_dict.get('offset', 0)

        sort = _sort(data_dict, fields_types)
        where = _where(data_dict, fields_types)

        select_cols = [u'"{0}"'.format(field_id) for field_id in field_ids] +\
                      [u'count(*) over() as "_full_count" %s' % rank_column]

        query_dict['distinct'] = data_dict.get('distinct', False)
        query_dict['select'] += select_cols
        query_dict['ts_query'] = ts_query
        query_dict['sort'] += sort
        query_dict['where'] += where
        query_dict['limit'] = limit
        query_dict['offset'] = offset

        return query_dict
