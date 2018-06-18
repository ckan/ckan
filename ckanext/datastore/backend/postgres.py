# -*- coding: utf-8 -*-

import copy
import logging
import sys
import sqlalchemy
import os
import pprint
import sqlalchemy.engine.url as sa_url
import urllib
import urllib2
import urlparse
import datetime
import hashlib
import json
from cStringIO import StringIO

from six import string_types, text_type

import ckan.lib.cli as cli
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckan.lib.lazyjson import LazyJSONObject

import ckanext.datastore.helpers as datastore_helpers
import ckanext.datastore.interfaces as interfaces

from psycopg2.extras import register_default_json, register_composite
import distutils.version
from sqlalchemy.exc import (ProgrammingError, IntegrityError,
                            DBAPIError, DataError)

import ckan.model as model
import ckan.plugins as plugins
from ckan.common import config, OrderedDict

from ckanext.datastore.backend import (
    DatastoreBackend,
    DatastoreException,
    _parse_sort_clause
)
from ckanext.datastore.backend import InvalidDataError

log = logging.getLogger(__name__)

_pg_types = {}
_type_names = set()
_engines = {}

_TIMEOUT = 60000  # milliseconds

# See http://www.postgresql.org/docs/9.2/static/errcodes-appendix.html
_PG_ERR_CODE = {
    'unique_violation': '23505',
    'query_canceled': '57014',
    'undefined_object': '42704',
    'syntax_error': '42601',
    'permission_denied': '42501',
    'duplicate_table': '42P07',
    'duplicate_alias': '42712',
}

_DATE_FORMATS = ['%Y-%m-%d',
                 '%Y-%m-%d %H:%M:%S',
                 '%Y-%m-%dT%H:%M:%S',
                 '%Y-%m-%dT%H:%M:%SZ',
                 '%d/%m/%Y',
                 '%m/%d/%Y',
                 '%d-%m-%Y',
                 '%m-%d-%Y']

_INSERT = 'insert'
_UPSERT = 'upsert'
_UPDATE = 'update'


if not os.environ.get('DATASTORE_LOAD'):
    ValidationError = toolkit.ValidationError
else:
    log.warn("Running datastore without CKAN")

    class ValidationError(Exception):
        def __init__(self, error_dict):
            pprint.pprint(error_dict)

is_single_statement = datastore_helpers.is_single_statement

_engines = {}


def literal_string(s):
    """
    Return s as a postgres literal string
    """
    return u"'" + s.replace(u"'", u"''").replace(u'\0', '') + u"'"


def identifier(s):
    """
    Return s as a quoted postgres identifier
    """
    return u'"' + s.replace(u'"', u'""').replace(u'\0', '') + u'"'


def get_read_engine():
    return _get_engine_from_url(config['ckan.datastore.read_url'])


def get_write_engine():
    return _get_engine_from_url(config['ckan.datastore.write_url'])


def _get_engine_from_url(connection_url):
    '''Get either read or write engine.'''
    engine = _engines.get(connection_url)
    if not engine:
        extras = {'url': connection_url}
        engine = sqlalchemy.engine_from_config(config,
                                               'ckan.datastore.sqlalchemy.',
                                               **extras)
        _engines[connection_url] = engine

    # don't automatically convert to python objects
    # when using native json types in 9.2+
    # http://initd.org/psycopg/docs/extras.html#adapt-json
    register_default_json(conn_or_curs=engine.raw_connection().connection,
                          globally=False,
                          loads=lambda x: x)

    return engine


def _dispose_engines():
    '''Dispose all database engines.'''
    global _engines
    for url, engine in _engines.items():
        engine.dispose()
    _engines = {}


def _pluck(field, arr):
    return [x[field] for x in arr]


def _rename_json_field(data_dict):
    '''Rename json type to a corresponding type for the datastore since
    pre 9.2 postgres versions do not support native json'''
    return _rename_field(data_dict, 'json', 'nested')


def _unrename_json_field(data_dict):
    return _rename_field(data_dict, 'nested', 'json')


def _rename_field(data_dict, term, replace):
    fields = data_dict.get('fields', [])
    for i, field in enumerate(fields):
        if 'type' in field and field['type'] == term:
            data_dict['fields'][i]['type'] = replace
    return data_dict


def _get_fields_types(context, data_dict):
    all_fields = _get_fields(context, data_dict)
    all_fields.insert(0, {'id': '_id', 'type': 'int'})
    field_types = OrderedDict([(f['id'], f['type']) for f in all_fields])
    return field_types


def _get_type(context, oid):
    _cache_types(context)
    return _pg_types[oid]


def _guess_type(field):
    '''Simple guess type of field, only allowed are
    integer, numeric and text'''
    data_types = set([int, float])
    if isinstance(field, (dict, list)):
        return 'nested'
    if isinstance(field, int):
        return 'int'
    if isinstance(field, float):
        return 'float'
    for data_type in list(data_types):
        try:
            data_type(field)
        except (TypeError, ValueError):
            data_types.discard(data_type)
            if not data_types:
                break
    if int in data_types:
        return 'integer'
    elif float in data_types:
        return 'numeric'

    # try iso dates
    for format in _DATE_FORMATS:
        try:
            datetime.datetime.strptime(field, format)
            return 'timestamp'
        except (ValueError, TypeError):
            continue
    return 'text'


def _get_unique_key(context, data_dict):
    sql_get_unique_key = '''
    SELECT
        a.attname AS column_names
    FROM
        pg_class t,
        pg_index idx,
        pg_attribute a
    WHERE
        t.oid = idx.indrelid
        AND a.attrelid = t.oid
        AND a.attnum = ANY(idx.indkey)
        AND t.relkind = 'r'
        AND idx.indisunique = true
        AND idx.indisprimary = false
        AND t.relname = %s
    '''
    key_parts = context['connection'].execute(sql_get_unique_key,
                                              data_dict['resource_id'])
    return [x[0] for x in key_parts]


def _get_field_info(connection, resource_id):
    u'''return a dictionary mapping column names to their info data,
    when present'''
    qtext = sqlalchemy.text(u'''
        select pa.attname as name, pd.description as info
        from pg_class pc, pg_attribute pa, pg_description pd
        where pa.attrelid = pc.oid and pd.objoid = pc.oid
            and pd.objsubid = pa.attnum and pc.relname = :res_id
            and pa.attnum > 0
    ''')
    try:
        return dict(
            (n, json.loads(v)) for (n, v) in
            connection.execute(qtext, res_id=resource_id).fetchall())
    except ValueError:  # don't die on non-json comments
        return {}


def _get_fields(context, data_dict):
    fields = []
    all_fields = context['connection'].execute(
        u'SELECT * FROM "{0}" LIMIT 1'.format(data_dict['resource_id'])
    )
    for field in all_fields.cursor.description:
        if not field[0].startswith('_'):
            fields.append({
                'id': field[0].decode('utf-8'),
                'type': _get_type(context, field[1])
            })
    return fields


def _cache_types(context):
    if not _pg_types:
        connection = context['connection']
        results = connection.execute(
            'SELECT oid, typname FROM pg_type;'
        )
        for result in results:
            _pg_types[result[0]] = result[1]
            _type_names.add(result[1])
        if 'nested' not in _type_names:
            native_json = _pg_version_is_at_least(connection, '9.2')

            log.info("Create nested type. Native JSON: {0!r}".format(
                native_json))

            backend = DatastorePostgresqlBackend.get_active_backend()
            engine = backend._get_write_engine()
            with engine.begin() as connection:
                connection.execute(
                    'CREATE TYPE "nested" AS (json {0}, extra text)'.format(
                        'json' if native_json else 'text'))
            _pg_types.clear()

            # redo cache types with json now available.
            return _cache_types(context)

        register_composite('nested', connection.connection, True)


def _pg_version_is_at_least(connection, version):
    try:
        v = distutils.version.LooseVersion(version)
        pg_version = connection.execute('select version();').fetchone()
        pg_version_number = pg_version[0].split()[1]
        pv = distutils.version.LooseVersion(pg_version_number)
        return v <= pv
    except ValueError:
        return False


def _get_read_only_user(data_dict):
    parsed = cli.parse_db_config('ckan.datastore.read_url')
    return parsed['db_user']


def _is_array_type(field_type):
    return field_type.startswith('_')


def _validate_record(record, num, field_names):
    # check record for sanity
    if not isinstance(record, dict):
        raise ValidationError({
            'records': [u'row "{0}" is not a json object'.format(num)]
        })
    # check for extra fields in data
    extra_keys = set(record.keys()) - set(field_names)

    if extra_keys:
        raise ValidationError({
            'records': [u'row "{0}" has extra keys "{1}"'.format(
                num + 1,
                ', '.join(list(extra_keys))
            )]
        })


def _where_clauses(data_dict, fields_types):
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
        if isinstance(q, string_types):
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
                              u'@@ {2}').format(
                                  literal_string(lang),
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
    if isinstance(q, string_types):
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
    rank_columns_str = ', '.join(rank_columns)
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


def _sort(data_dict, fields_types):
    sort = data_dict.get('sort')
    if not sort:
        q = data_dict.get('q')
        if q:
            if isinstance(q, string_types):
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
            u'{0} {1}'.format(identifier(field), sort))

    return clause_parsed


def _ts_query_alias(field=None):
    query_alias = u'query'
    if field:
        query_alias += u' ' + field
    return u'"{0}"'.format(query_alias)


def _get_aliases(context, data_dict):
    '''Get a list of aliases for a resource.'''
    res_id = data_dict['resource_id']
    alias_sql = sqlalchemy.text(
        u'SELECT name FROM "_table_metadata" WHERE alias_of = :id')
    results = context['connection'].execute(alias_sql, id=res_id).fetchall()
    return [x[0] for x in results]


def _get_resources(context, alias):
    '''Get a list of resources for an alias. There could be more than one alias
    in a resource_dict.'''
    alias_sql = sqlalchemy.text(
        u'''SELECT alias_of FROM "_table_metadata"
        WHERE name = :alias AND alias_of IS NOT NULL''')
    results = context['connection'].execute(alias_sql, alias=alias).fetchall()
    return [x[0] for x in results]


def create_alias(context, data_dict):
    aliases = datastore_helpers.get_list(data_dict.get('aliases'))
    if aliases is not None:
        # delete previous aliases
        previous_aliases = _get_aliases(context, data_dict)
        for alias in previous_aliases:
            sql_alias_drop_string = u'DROP VIEW "{0}"'.format(alias)
            context['connection'].execute(sql_alias_drop_string)

        try:
            for alias in aliases:
                sql_alias_string = u'''CREATE VIEW "{alias}"
                    AS SELECT * FROM "{main}"'''.format(
                    alias=alias,
                    main=data_dict['resource_id']
                )

                res_ids = _get_resources(context, alias)
                if res_ids:
                    raise ValidationError({
                        'alias': [(u'The alias "{0}" already exists.').format(
                            alias)]
                    })

                context['connection'].execute(sql_alias_string)
        except DBAPIError as e:
            if e.orig.pgcode in [_PG_ERR_CODE['duplicate_table'],
                                 _PG_ERR_CODE['duplicate_alias']]:
                raise ValidationError({
                    'alias': [u'"{0}" already exists'.format(alias)]
                })


def _generate_index_name(resource_id, field):
    value = (resource_id + field).encode('utf-8')
    return hashlib.sha1(value).hexdigest()


def _get_fts_index_method():
    method = config.get('ckan.datastore.default_fts_index_method')
    return method or 'gist'


def _build_fts_indexes(connection, data_dict, sql_index_str_method, fields):
    fts_indexes = []
    resource_id = data_dict['resource_id']
    # FIXME: This is repeated on the plugin.py, we should keep it DRY
    default_fts_lang = config.get('ckan.datastore.default_fts_lang')
    if default_fts_lang is None:
        default_fts_lang = u'english'
    fts_lang = data_dict.get('lang', default_fts_lang)

    # create full-text search indexes
    def to_tsvector(x):
        return u"to_tsvector('{0}', {1})".format(fts_lang, x)

    def cast_as_text(x):
        return u'cast("{0}" AS text)'.format(x)

    full_text_field = {'type': 'tsvector', 'id': '_full_text'}
    for field in [full_text_field] + fields:
        if not datastore_helpers.should_fts_index_field_type(field['type']):
            continue

        field_str = field['id']
        if field['type'] not in ['text', 'tsvector']:
            field_str = cast_as_text(field_str)
        else:
            field_str = u'"{0}"'.format(field_str)
        if field['type'] != 'tsvector':
            field_str = to_tsvector(field_str)
        fts_indexes.append(sql_index_str_method.format(
            res_id=resource_id,
            unique='',
            name=_generate_index_name(resource_id, field_str),
            method=_get_fts_index_method(), fields=field_str))

    return fts_indexes


def _drop_indexes(context, data_dict, unique=False):
    sql_drop_index = u'DROP INDEX "{0}" CASCADE'
    sql_get_index_string = u"""
        SELECT
            i.relname AS index_name
        FROM
            pg_class t,
            pg_class i,
            pg_index idx
        WHERE
            t.oid = idx.indrelid
            AND i.oid = idx.indexrelid
            AND t.relkind = 'r'
            AND idx.indisunique = {unique}
            AND idx.indisprimary = false
            AND t.relname = %s
        """.format(unique='true' if unique else 'false')
    indexes_to_drop = context['connection'].execute(
        sql_get_index_string, data_dict['resource_id']).fetchall()
    for index in indexes_to_drop:
        context['connection'].execute(
            sql_drop_index.format(index[0]).replace('%', '%%'))


def _get_index_names(connection, resource_id):
    sql = u"""
        SELECT
            i.relname AS index_name
        FROM
            pg_class t,
            pg_class i,
            pg_index idx
        WHERE
            t.oid = idx.indrelid
            AND i.oid = idx.indexrelid
            AND t.relkind = 'r'
            AND t.relname = %s
        """
    results = connection.execute(sql, resource_id).fetchall()
    return [result[0] for result in results]


def _is_valid_pg_type(context, type_name):
    if type_name in _type_names:
        return True
    else:
        connection = context['connection']
        try:
            connection.execute('SELECT %s::regtype', type_name)
        except ProgrammingError as e:
            if e.orig.pgcode in [_PG_ERR_CODE['undefined_object'],
                                 _PG_ERR_CODE['syntax_error']]:
                return False
            raise
        else:
            return True


def _execute_single_statement(context, sql_string, where_values):
    if not datastore_helpers.is_single_statement(sql_string):
        raise ValidationError({
            'query': ['Query is not a single statement.']
        })

    results = context['connection'].execute(sql_string, [where_values])

    return results


def _insert_links(data_dict, limit, offset):
    '''Adds link to the next/prev part (same limit, offset=offset+limit)
    and the resource page.'''
    data_dict['_links'] = {}

    # get the url from the request
    try:
        urlstring = toolkit.request.environ['CKAN_CURRENT_URL']
    except (KeyError, TypeError):
        return  # no links required for local actions

    # change the offset in the url
    parsed = list(urlparse.urlparse(urlstring))
    query = urllib2.unquote(parsed[4])

    arguments = dict(urlparse.parse_qsl(query))
    arguments_start = dict(arguments)
    arguments_prev = dict(arguments)
    arguments_next = dict(arguments)
    if 'offset' in arguments_start:
        arguments_start.pop('offset')
    arguments_next['offset'] = int(offset) + int(limit)
    arguments_prev['offset'] = int(offset) - int(limit)

    parsed_start = parsed[:]
    parsed_prev = parsed[:]
    parsed_next = parsed[:]
    parsed_start[4] = urllib.urlencode(arguments_start)
    parsed_next[4] = urllib.urlencode(arguments_next)
    parsed_prev[4] = urllib.urlencode(arguments_prev)

    # add the links to the data dict
    data_dict['_links']['start'] = urlparse.urlunparse(parsed_start)
    data_dict['_links']['next'] = urlparse.urlunparse(parsed_next)
    if int(offset) - int(limit) > 0:
        data_dict['_links']['prev'] = urlparse.urlunparse(parsed_prev)


def _where(where_clauses_and_values):
    '''Return a SQL WHERE clause from list with clauses and values

    :param where_clauses_and_values: list of tuples with format
        (where_clause, param1, ...)
    :type where_clauses_and_values: list of tuples

    :returns: SQL WHERE string with placeholders for the parameters, and list
        of parameters
    :rtype: string
    '''
    where_clauses = []
    values = []

    for clause_and_values in where_clauses_and_values:
        where_clauses.append('(' + clause_and_values[0] + ')')
        values += clause_and_values[1:]

    where_clause = u' AND '.join(where_clauses)
    if where_clause:
        where_clause = u'WHERE ' + where_clause

    return where_clause, values


def convert(data, type_name):
    if data is None:
        return None
    if type_name == 'nested':
        return json.loads(data[0])
    # array type
    if type_name.startswith('_'):
        sub_type = type_name[1:]
        return [convert(item, sub_type) for item in data]
    if type_name == 'tsvector':
        return text_type(data, 'utf-8')
    if isinstance(data, datetime.datetime):
        return data.isoformat()
    if isinstance(data, (int, float)):
        return data
    return text_type(data)


def check_fields(context, fields):
    '''Check if field types are valid.'''
    for field in fields:
        if field.get('type') and not _is_valid_pg_type(context, field['type']):
            raise ValidationError({
                'fields': [u'"{0}" is not a valid field type'.format(
                    field['type'])]
            })
        elif not datastore_helpers.is_valid_field_name(field['id']):
            raise ValidationError({
                'fields': [u'"{0}" is not a valid field name'.format(
                    field['id'])]
            })


def create_indexes(context, data_dict):
    connection = context['connection']
    indexes = datastore_helpers.get_list(data_dict.get('indexes'))
    # primary key is not a real primary key
    # it's just a unique key
    primary_key = datastore_helpers.get_list(data_dict.get('primary_key'))

    sql_index_tmpl = u'CREATE {unique} INDEX "{name}" ON "{res_id}"'
    sql_index_string_method = sql_index_tmpl + u' USING {method}({fields})'
    sql_index_string = sql_index_tmpl + u' ({fields})'
    sql_index_strings = []

    fields = _get_fields(context, data_dict)
    field_ids = _pluck('id', fields)
    json_fields = [x['id'] for x in fields if x['type'] == 'nested']

    fts_indexes = _build_fts_indexes(connection,
                                     data_dict,
                                     sql_index_string_method,
                                     fields)
    sql_index_strings = sql_index_strings + fts_indexes

    if indexes is not None:
        _drop_indexes(context, data_dict, False)
    else:
        indexes = []

    if primary_key is not None:
        unique_keys = _get_unique_key(context, data_dict)
        if sorted(unique_keys) != sorted(primary_key):
            _drop_indexes(context, data_dict, True)
            indexes.append(primary_key)

    for index in indexes:
        if not index:
            continue

        index_fields = datastore_helpers.get_list(index)
        for field in index_fields:
            if field not in field_ids:
                raise ValidationError({
                    'index': [
                        u'The field "{0}" is not a valid column name.'.format(
                            index)]
                })
        fields_string = u', '.join(
            ['(("{0}").json::text)'.format(field)
                if field in json_fields else
                '"%s"' % field
                for field in index_fields])
        sql_index_strings.append(sql_index_string.format(
            res_id=data_dict['resource_id'],
            unique='unique' if index == primary_key else '',
            name=_generate_index_name(data_dict['resource_id'], fields_string),
            fields=fields_string))

    sql_index_strings = map(lambda x: x.replace('%', '%%'), sql_index_strings)
    current_indexes = _get_index_names(context['connection'],
                                       data_dict['resource_id'])
    for sql_index_string in sql_index_strings:
        has_index = [c for c in current_indexes
                     if sql_index_string.find(c) != -1]
        if not has_index:
            connection.execute(sql_index_string)


def create_table(context, data_dict):
    '''Creates table, columns and column info (stored as comments).

    :param resource_id: The resource ID (i.e. postgres table name)
    :type resource_id: string
    :param fields: details of each field/column, each with properties:
        id - field/column name
        type - optional, otherwise it is guessed from the first record
        info - some field/column properties, saved as a JSON string in postgres
            as a column comment. e.g. "type_override", "label", "notes"
    :type fields: list of dicts
    :param records: records, of which the first is used when a field type needs
        guessing.
    :type records: list of dicts
    '''

    datastore_fields = [
        {'id': '_id', 'type': 'serial primary key'},
        {'id': '_full_text', 'type': 'tsvector'},
    ]

    # check first row of data for additional fields
    extra_fields = []
    supplied_fields = data_dict.get('fields', [])
    check_fields(context, supplied_fields)
    field_ids = _pluck('id', supplied_fields)
    records = data_dict.get('records')

    fields_errors = []

    for field_id in field_ids:
        # Postgres has a limit of 63 characters for a column name
        if len(field_id) > 63:
            message = 'Column heading "{0}" exceeds limit of 63 '\
                'characters.'.format(field_id)
            fields_errors.append(message)

    if fields_errors:
        raise ValidationError({
            'fields': fields_errors
        })

    # if type is field is not given try and guess or throw an error
    for field in supplied_fields:
        if 'type' not in field:
            if not records or field['id'] not in records[0]:
                raise ValidationError({
                    'fields': [u'"{0}" type not guessable'.format(field['id'])]
                })
            field['type'] = _guess_type(records[0][field['id']])

    # Check for duplicate fields
    unique_fields = set([f['id'] for f in supplied_fields])
    if not len(unique_fields) == len(supplied_fields):
        raise ValidationError({
            'field': ['Duplicate column names are not supported']
        })

    if records:
        # check record for sanity
        if not isinstance(records[0], dict):
            raise ValidationError({
                'records': ['The first row is not a json object']
            })
        supplied_field_ids = records[0].keys()
        for field_id in supplied_field_ids:
            if field_id not in field_ids:
                extra_fields.append({
                    'id': field_id,
                    'type': _guess_type(records[0][field_id])
                })

    fields = datastore_fields + supplied_fields + extra_fields
    sql_fields = u", ".join([u'{0} {1}'.format(
        identifier(f['id']), f['type']) for f in fields])

    sql_string = u'CREATE TABLE {0} ({1});'.format(
        identifier(data_dict['resource_id']),
        sql_fields
    )

    info_sql = []
    for f in supplied_fields:
        info = f.get(u'info')
        if isinstance(info, dict):
            info_sql.append(u'COMMENT ON COLUMN {0}.{1} is {2}'.format(
                identifier(data_dict['resource_id']),
                identifier(f['id']),
                literal_string(
                    json.dumps(info, ensure_ascii=False))))

    context['connection'].execute(
        (sql_string + u';'.join(info_sql)).replace(u'%', u'%%'))


def alter_table(context, data_dict):
    '''Adds new columns and updates column info (stored as comments).

    :param resource_id: The resource ID (i.e. postgres table name)
    :type resource_id: string
    :param fields: details of each field/column, each with properties:
        id - field/column name
        type - optional, otherwise it is guessed from the first record
        info - some field/column properties, saved as a JSON string in postgres
            as a column comment. e.g. "type_override", "label", "notes"
    :type fields: list of dicts
    :param records: records, of which the first is used when a field type needs
        guessing.
    :type records: list of dicts
    '''
    supplied_fields = data_dict.get('fields', [])
    current_fields = _get_fields(context, data_dict)
    if not supplied_fields:
        supplied_fields = current_fields
    check_fields(context, supplied_fields)
    field_ids = _pluck('id', supplied_fields)
    records = data_dict.get('records')
    new_fields = []

    for num, field in enumerate(supplied_fields):
        # check to see if field definition is the same or and
        # extension of current fields
        if num < len(current_fields):
            if field['id'] != current_fields[num]['id']:
                raise ValidationError({
                    'fields': [(u'Supplied field "{0}" not '
                                u'present or in wrong order').format(
                        field['id'])]
                })
            # no need to check type as field already defined.
            continue

        if 'type' not in field:
            if not records or field['id'] not in records[0]:
                raise ValidationError({
                    'fields': [u'"{0}" type not guessable'.format(field['id'])]
                })
            field['type'] = _guess_type(records[0][field['id']])
        new_fields.append(field)

    if records:
        # check record for sanity as they have not been
        # checked during validation
        if not isinstance(records, list):
            raise ValidationError({
                'records': ['Records has to be a list of dicts']
            })
        if not isinstance(records[0], dict):
            raise ValidationError({
                'records': ['The first row is not a json object']
            })
        supplied_field_ids = records[0].keys()
        for field_id in supplied_field_ids:
            if field_id not in field_ids:
                new_fields.append({
                    'id': field_id,
                    'type': _guess_type(records[0][field_id])
                })

    alter_sql = []
    for f in new_fields:
        alter_sql.append(u'ALTER TABLE {0} ADD {1} {2};'.format(
            identifier(data_dict['resource_id']),
            identifier(f['id']),
            f['type']))

    for f in supplied_fields:
        if u'info' in f:
            info = f.get(u'info')
            if isinstance(info, dict):
                info_sql = literal_string(
                    json.dumps(info, ensure_ascii=False))
            else:
                info_sql = 'NULL'
            alter_sql.append(u'COMMENT ON COLUMN {0}.{1} is {2}'.format(
                identifier(data_dict['resource_id']),
                identifier(f['id']),
                info_sql))

    if alter_sql:
        context['connection'].execute(
            u';'.join(alter_sql).replace(u'%', u'%%'))


def insert_data(context, data_dict):
    """

    :raises InvalidDataError: if there is an invalid value in the given data

    """
    data_dict['method'] = _INSERT
    result = upsert_data(context, data_dict)
    return result


def upsert_data(context, data_dict):
    '''insert all data from records'''
    if not data_dict.get('records'):
        return

    method = data_dict.get('method', _UPSERT)

    fields = _get_fields(context, data_dict)
    field_names = _pluck('id', fields)
    records = data_dict['records']
    sql_columns = ", ".join(
        identifier(name) for name in field_names)

    if method == _INSERT:
        rows = []
        for num, record in enumerate(records):
            _validate_record(record, num, field_names)

            row = []
            for field in fields:
                value = record.get(field['id'])
                if value and field['type'].lower() == 'nested':
                    # a tuple with an empty second value
                    value = (json.dumps(value), '')
                row.append(value)
            rows.append(row)

        sql_string = u'''INSERT INTO {res_id} ({columns})
            VALUES ({values});'''.format(
            res_id=identifier(data_dict['resource_id']),
            columns=sql_columns.replace('%', '%%'),
            values=', '.join(['%s' for field in field_names])
        )

        try:
            context['connection'].execute(sql_string, rows)
        except sqlalchemy.exc.DataError:
            raise InvalidDataError(
                toolkit._("The data was invalid (for example: a numeric value "
                          "is out of range or was inserted into a text field)."
                          ))
        except sqlalchemy.exc.DatabaseError as err:
            raise ValidationError(
                {u'records': [_programming_error_summary(err)]})

    elif method in [_UPDATE, _UPSERT]:
        unique_keys = _get_unique_key(context, data_dict)
        if len(unique_keys) < 1:
            raise ValidationError({
                'table': [u'table does not have a unique key defined']
            })

        for num, record in enumerate(records):
            # all key columns have to be defined
            missing_fields = [field for field in unique_keys
                              if field not in record]
            if missing_fields:
                raise ValidationError({
                    'key': [u'''fields "{fields}" are missing
                        but needed as key'''.format(
                            fields=', '.join(missing_fields))]
                })

            for field in fields:
                value = record.get(field['id'])
                if value is not None and field['type'].lower() == 'nested':
                    # a tuple with an empty second value
                    record[field['id']] = (json.dumps(value), '')

            non_existing_filed_names = [field for field in record
                                        if field not in field_names]
            if non_existing_filed_names:
                raise ValidationError({
                    'fields': [u'fields "{0}" do not exist'.format(
                        ', '.join(non_existing_filed_names))]
                })

            unique_values = [record[key] for key in unique_keys]

            used_fields = [field for field in fields
                           if field['id'] in record]

            used_field_names = _pluck('id', used_fields)

            used_values = [record[field] for field in used_field_names]

            if method == _UPDATE:
                sql_string = u'''
                    UPDATE "{res_id}"
                    SET ({columns}, "_full_text") = ({values}, NULL)
                    WHERE ({primary_key}) = ({primary_value});
                '''.format(
                    res_id=data_dict['resource_id'],
                    columns=u', '.join(
                        [identifier(field)
                         for field in used_field_names]).replace('%', '%%'),
                    values=u', '.join(
                        ['%s' for _ in used_field_names]),
                    primary_key=u','.join(
                        [u'"{0}"'.format(part) for part in unique_keys]),
                    primary_value=u','.join(["%s"] * len(unique_keys))
                )
                try:
                    results = context['connection'].execute(
                        sql_string, used_values + unique_values)
                except sqlalchemy.exc.DatabaseError as err:
                    raise ValidationError({
                        u'records': [_programming_error_summary(err)],
                        u'_records_row': num})

                # validate that exactly one row has been updated
                if results.rowcount != 1:
                    raise ValidationError({
                        'key': [u'key "{0}" not found'.format(unique_values)]
                    })

            elif method == _UPSERT:
                sql_string = u'''
                    UPDATE "{res_id}"
                    SET ({columns}, "_full_text") = ({values}, NULL)
                    WHERE ({primary_key}) = ({primary_value});
                    INSERT INTO "{res_id}" ({columns})
                           SELECT {values}
                           WHERE NOT EXISTS (SELECT 1 FROM "{res_id}"
                                    WHERE ({primary_key}) = ({primary_value}));
                '''.format(
                    res_id=data_dict['resource_id'],
                    columns=u', '.join([u'"{0}"'.format(field)
                                        for field in used_field_names]),
                    values=u', '.join(['%s::nested'
                                       if field['type'] == 'nested' else '%s'
                                       for field in used_fields]),
                    primary_key=u','.join([u'"{0}"'.format(part)
                                           for part in unique_keys]),
                    primary_value=u','.join(["%s"] * len(unique_keys))
                )
                try:
                    context['connection'].execute(
                        sql_string,
                        (used_values + unique_values) * 2)
                except sqlalchemy.exc.DatabaseError as err:
                    raise ValidationError({
                        u'records': [_programming_error_summary(err)],
                        u'_records_row': num})


def validate(context, data_dict):
    fields_types = _get_fields_types(context, data_dict)
    data_dict_copy = copy.deepcopy(data_dict)

    # TODO: Convert all attributes that can be a comma-separated string to
    # lists
    if 'fields' in data_dict_copy:
        fields = datastore_helpers.get_list(data_dict_copy['fields'])
        data_dict_copy['fields'] = fields
    if 'sort' in data_dict_copy:
        fields = datastore_helpers.get_list(data_dict_copy['sort'], False)
        data_dict_copy['sort'] = fields

    for plugin in plugins.PluginImplementations(interfaces.IDatastore):
        data_dict_copy = plugin.datastore_validate(context,
                                                   data_dict_copy,
                                                   fields_types)

    # Remove default elements in data_dict
    data_dict_copy.pop('connection_url', None)
    data_dict_copy.pop('resource_id', None)

    data_dict_copy.pop('id', None)
    data_dict_copy.pop('include_total', None)
    data_dict_copy.pop('records_format', None)

    for key, values in data_dict_copy.iteritems():
        if not values:
            continue
        if isinstance(values, string_types):
            value = values
        elif isinstance(values, (list, tuple)):
            value = values[0]
        elif isinstance(values, dict):
            value = values.keys()[0]
        else:
            value = values

        raise ValidationError({
            key: [u'invalid value "{0}"'.format(value)]
        })

    return True


def search_data(context, data_dict):
    validate(context, data_dict)
    fields_types = _get_fields_types(context, data_dict)

    query_dict = {
        'select': [],
        'sort': [],
        'where': []
    }

    for plugin in p.PluginImplementations(interfaces.IDatastore):
        query_dict = plugin.datastore_search(context, data_dict,
                                             fields_types, query_dict)

    where_clause, where_values = _where(query_dict['where'])

    # FIXME: Remove duplicates on select columns
    select_columns = ', '.join(query_dict['select']).replace('%', '%%')
    ts_query = query_dict['ts_query'].replace('%', '%%')
    resource_id = data_dict['resource_id'].replace('%', '%%')
    sort = query_dict['sort']
    limit = query_dict['limit']
    offset = query_dict['offset']

    if query_dict.get('distinct'):
        distinct = 'DISTINCT'
    else:
        distinct = ''

    if sort:
        sort_clause = 'ORDER BY %s' % (', '.join(sort)).replace('%', '%%')
    else:
        sort_clause = ''

    records_format = data_dict['records_format']
    if records_format == u'objects':
        sql_fmt = u'''
            SELECT array_to_json(array_agg(j))::text FROM (
                SELECT {distinct} {select}
                FROM "{resource}" {ts_query}
                {where} {sort} LIMIT {limit} OFFSET {offset}
            ) AS j'''
    elif records_format == u'lists':
        select_columns = u" || ',' || ".join(
            s for s in query_dict['select']
        ).replace('%', '%%')
        sql_fmt = u'''
            SELECT '[' || array_to_string(array_agg(j.v), ',') || ']' FROM (
                SELECT '[' || {select} || ']' v
                FROM (
                    SELECT {distinct} * FROM "{resource}" {ts_query}
                    {where} {sort} LIMIT {limit} OFFSET {offset}) as z
            ) AS j'''
    elif records_format == u'csv':
        sql_fmt = u'''
            COPY (
                SELECT {distinct} {select}
                FROM "{resource}" {ts_query}
                {where} {sort} LIMIT {limit} OFFSET {offset}
            ) TO STDOUT csv DELIMITER ',' '''
    elif records_format == u'tsv':
        sql_fmt = u'''
            COPY (
                SELECT {distinct} {select}
                FROM "{resource}" {ts_query}
                {where} {sort} LIMIT {limit} OFFSET {offset}
            ) TO STDOUT csv DELIMITER '\t' '''

    sql_string = sql_fmt.format(
        distinct=distinct,
        select=select_columns,
        resource=resource_id,
        ts_query=ts_query,
        where=where_clause,
        sort=sort_clause,
        limit=limit,
        offset=offset)
    if records_format == u'csv' or records_format == u'tsv':
        buf = StringIO()
        _execute_single_statement_copy_to(
            context, sql_string, where_values, buf)
        records = buf.getvalue()
    else:
        v = list(_execute_single_statement(
            context, sql_string, where_values))[0][0]
        if v is None:
            records = []
        else:
            records = LazyJSONObject(v)
    data_dict['records'] = records

    field_info = _get_field_info(
        context['connection'], data_dict['resource_id'])
    result_fields = []
    for field_id, field_type in fields_types.iteritems():
        f = {u'id': field_id, u'type': field_type}
        if field_id in field_info:
            f['info'] = field_info[f['id']]
        result_fields.append(f)
    data_dict['fields'] = result_fields
    _unrename_json_field(data_dict)

    _insert_links(data_dict, limit, offset)

    if data_dict.get('include_total', True):
        count_sql_string = u'''SELECT {distinct} count(*)
            FROM "{resource}" {ts_query} {where};'''.format(
            distinct=distinct,
            resource=resource_id,
            ts_query=ts_query,
            where=where_clause)
        count_result = _execute_single_statement(
            context, count_sql_string, where_values)
        data_dict['total'] = count_result.fetchall()[0][0]

    return data_dict


def _execute_single_statement_copy_to(context, sql_string, where_values, buf):
    if not datastore_helpers.is_single_statement(sql_string):
        raise ValidationError({
            'query': ['Query is not a single statement.']
        })

    cursor = context['connection'].connection.cursor()
    cursor.copy_expert(cursor.mogrify(sql_string, where_values), buf)
    cursor.close()


def format_results(context, results, data_dict):
    result_fields = []
    for field in results.cursor.description:
        result_fields.append({
            'id': field[0].decode('utf-8'),
            'type': _get_type(context, field[1])
        })

    records = []
    for row in results:
        converted_row = {}
        for field in result_fields:
            converted_row[field['id']] = convert(row[field['id']],
                                                 field['type'])
        records.append(converted_row)
    data_dict['records'] = records
    data_dict['fields'] = result_fields

    return _unrename_json_field(data_dict)


def delete_data(context, data_dict):
    validate(context, data_dict)
    fields_types = _get_fields_types(context, data_dict)

    query_dict = {
        'where': []
    }

    for plugin in plugins.PluginImplementations(interfaces.IDatastore):
        query_dict = plugin.datastore_delete(context, data_dict,
                                             fields_types, query_dict)

    where_clause, where_values = _where(query_dict['where'])
    sql_string = u'DELETE FROM "{0}" {1}'.format(
        data_dict['resource_id'],
        where_clause
    )

    _execute_single_statement(context, sql_string, where_values)


def _create_triggers(connection, resource_id, triggers):
    u'''
    Delete existing triggers on table then create triggers

    Currently our schema requires "before insert or update"
    triggers run on each row, so we're not reading "when"
    or "for_each" parameters from triggers list.
    '''
    existing = connection.execute(
        u"""SELECT tgname FROM pg_trigger
        WHERE tgrelid = %s::regclass AND tgname LIKE 't___'""",
        resource_id)
    sql_list = (
        [u'DROP TRIGGER {name} ON {table}'.format(
            name=identifier(r[0]),
            table=identifier(resource_id))
         for r in existing] +
        [u'''CREATE TRIGGER {name}
        BEFORE INSERT OR UPDATE ON {table}
        FOR EACH ROW EXECUTE PROCEDURE {function}()'''.format(
            # 1000 triggers per table should be plenty
            name=identifier(u't%03d' % i),
            table=identifier(resource_id),
            function=identifier(t['function']))
         for i, t in enumerate(triggers)])
    try:
        if sql_list:
            connection.execute(u';\n'.join(sql_list))
    except ProgrammingError as pe:
        raise ValidationError({u'triggers': [_programming_error_summary(pe)]})


def _create_fulltext_trigger(connection, resource_id):
    connection.execute(
        u'''CREATE TRIGGER zfulltext
        BEFORE INSERT OR UPDATE ON {table}
        FOR EACH ROW EXECUTE PROCEDURE populate_full_text_trigger()'''.format(
            table=identifier(resource_id)))


def upsert(context, data_dict):
    '''
    This method combines upsert insert and update on the datastore. The method
    that will be used is defined in the mehtod variable.

    Any error results in total failure! For now pass back the actual error.
    Should be transactional.
    '''
    backend = DatastorePostgresqlBackend.get_active_backend()
    engine = backend._get_write_engine()
    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', _TIMEOUT)

    trans = context['connection'].begin()
    try:
        # check if table already existes
        context['connection'].execute(
            u'SET LOCAL statement_timeout TO {0}'.format(timeout))
        upsert_data(context, data_dict)
        trans.commit()
        return _unrename_json_field(data_dict)
    except IntegrityError as e:
        if e.orig.pgcode == _PG_ERR_CODE['unique_violation']:
            raise ValidationError({
                'constraints': ['Cannot insert records or create index because'
                                ' of uniqueness constraint'],
                'info': {
                    'orig': str(e.orig),
                    'pgcode': e.orig.pgcode
                }
            })
        raise
    except DataError as e:
        raise ValidationError({
            'data': e.message,
            'info': {
                'orig': [str(e.orig)]
            }})
    except DBAPIError as e:
        if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
            raise ValidationError({
                'query': ['Query took too long']
            })
        raise
    except Exception as e:
        trans.rollback()
        raise
    finally:
        context['connection'].close()


def search(context, data_dict):
    backend = DatastorePostgresqlBackend.get_active_backend()
    engine = backend._get_read_engine()
    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', _TIMEOUT)
    _cache_types(context)

    try:
        context['connection'].execute(
            u'SET LOCAL statement_timeout TO {0}'.format(timeout))
        return search_data(context, data_dict)
    except DBAPIError as e:
        if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
            raise ValidationError({
                'query': ['Search took too long']
            })
        raise ValidationError({
            'query': ['Invalid query'],
            'info': {
                'statement': [e.statement],
                'params': [e.params],
                'orig': [str(e.orig)]
            }
        })
    finally:
        context['connection'].close()


def search_sql(context, data_dict):
    backend = DatastorePostgresqlBackend.get_active_backend()
    engine = backend._get_read_engine()

    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', _TIMEOUT)
    _cache_types(context)

    sql = data_dict['sql'].replace('%', '%%')

    try:

        context['connection'].execute(
            u'SET LOCAL statement_timeout TO {0}'.format(timeout))

        table_names = datastore_helpers.get_table_names_from_sql(context, sql)
        log.debug('Tables involved in input SQL: {0!r}'.format(table_names))

        if any(t.startswith('pg_') for t in table_names):
            raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to access system tables']
            })
        context['check_access'](table_names)

        results = context['connection'].execute(sql)

        return format_results(context, results, data_dict)

    except ProgrammingError as e:
        if e.orig.pgcode == _PG_ERR_CODE['permission_denied']:
            raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to read resource.']
            })

        def _remove_explain(msg):
            return (msg.replace('EXPLAIN (VERBOSE, FORMAT JSON) ', '')
                       .replace('EXPLAIN ', ''))

        raise ValidationError({
            'query': [_remove_explain(str(e))],
            'info': {
                'statement': [_remove_explain(e.statement)],
                'params': [e.params],
                'orig': [_remove_explain(str(e.orig))]
            }
        })
    except DBAPIError as e:
        if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
            raise ValidationError({
                'query': ['Query took too long']
            })
        raise
    finally:
        context['connection'].close()


class DatastorePostgresqlBackend(DatastoreBackend):

    def _get_write_engine(self):
        return _get_engine_from_url(self.write_url)

    def _get_read_engine(self):
        return _get_engine_from_url(self.read_url)

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

        if self._same_read_and_write_url():
            self._log_or_raise('The write and read-only database '
                               'connection urls are the same.')

        if not self._read_connection_has_correct_privileges():
            self._log_or_raise('The read-only user has write privileges.')

    def _is_read_only_database(self):
        ''' Returns True if no connection has CREATE privileges on the public
        schema. This is the case if replication is enabled.'''
        for url in [self.ckan_url, self.write_url, self.read_url]:
            connection = _get_engine_from_url(url).connect()
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
        write_connection = self._get_write_engine().connect()
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

    def configure(self, config):
        self.config = config
        # check for ckan.datastore.write_url and ckan.datastore.read_url
        if ('ckan.datastore.write_url' not in config):
            error_msg = 'ckan.datastore.write_url not found in config'
            raise DatastoreException(error_msg)
        if ('ckan.datastore.read_url' not in config):
            error_msg = 'ckan.datastore.read_url not found in config'
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
        self.read_url = self.config['ckan.datastore.read_url']

        self.read_engine = self._get_read_engine()
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

    def datastore_delete(self, context, data_dict, fields_types, query_dict):
        query_dict['where'] += _where_clauses(data_dict, fields_types)
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
        where = _where_clauses(data_dict, fields_types)

        select_cols = []
        records_format = data_dict.get(u'records_format')
        json_values = records_format in (u'objects', u'lists')
        for field_id in field_ids:
            fmt = u'to_json({0})' if records_format == u'lists' else u'{0}'
            typ = fields_types.get(field_id)
            if typ == u'nested':
                fmt = u'({0}).json'
            elif typ == u'timestamp':
                fmt = u"to_char({0}, 'YYYY-MM-DD\"T\"HH24:MI:SS')"
                if json_values:
                    fmt = u"to_json({0})".format(fmt)
            elif typ.startswith(u'_') or typ.endswith(u'[]'):
                fmt = u'array_to_json({0})'
            if records_format == u'objects':
                fmt += u' as {0}'
            select_cols.append(fmt.format(
                identifier(field_id)))
        if rank_column:
            select_cols.append(rank_column)

        query_dict['distinct'] = data_dict.get('distinct', False)
        query_dict['select'] += select_cols
        query_dict['ts_query'] = ts_query
        query_dict['sort'] += sort
        query_dict['where'] += where
        query_dict['limit'] = limit
        query_dict['offset'] = offset

        return query_dict

    def delete(self, context, data_dict):
        engine = self._get_write_engine()
        context['connection'] = engine.connect()
        _cache_types(context)

        trans = context['connection'].begin()
        try:
            # check if table exists
            if 'filters' not in data_dict:
                context['connection'].execute(
                    u'DROP TABLE "{0}" CASCADE'.format(
                        data_dict['resource_id'])
                )
            else:
                delete_data(context, data_dict)

            trans.commit()
            return _unrename_json_field(data_dict)
        except Exception:
            trans.rollback()
            raise
        finally:
            context['connection'].close()

    def create(self, context, data_dict):
        '''
        The first row will be used to guess types not in the fields and the
        guessed types will be added to the headers permanently.
        Consecutive rows have to conform to the field definitions.
        rows can be empty so that you can just set the fields.
        fields are optional but needed if you want to do type hinting or
        add extra information for certain columns or to explicitly
        define ordering.
        eg: [{"id": "dob", "type": "timestamp"},
             {"id": "name", "type": "text"}]
        A header items values can not be changed after it has been defined
        nor can the ordering of them be changed. They can be extended though.
        Any error results in total failure! For now pass back the actual error.
        Should be transactional.
        :raises InvalidDataError: if there is an invalid value in the given
                                  data
        '''
        engine = get_write_engine()
        context['connection'] = engine.connect()
        timeout = context.get('query_timeout', _TIMEOUT)
        _cache_types(context)

        _rename_json_field(data_dict)

        trans = context['connection'].begin()
        try:
            # check if table already existes
            context['connection'].execute(
                u'SET LOCAL statement_timeout TO {0}'.format(timeout))
            result = context['connection'].execute(
                u'SELECT * FROM pg_tables WHERE tablename = %s',
                data_dict['resource_id']
            ).fetchone()
            if not result:
                create_table(context, data_dict)
                _create_fulltext_trigger(
                    context['connection'],
                    data_dict['resource_id'])
            else:
                alter_table(context, data_dict)
            if 'triggers' in data_dict:
                _create_triggers(
                    context['connection'],
                    data_dict['resource_id'],
                    data_dict['triggers'])
            insert_data(context, data_dict)
            create_indexes(context, data_dict)
            create_alias(context, data_dict)
            trans.commit()
            return _unrename_json_field(data_dict)
        except IntegrityError as e:
            if e.orig.pgcode == _PG_ERR_CODE['unique_violation']:
                raise ValidationError({
                    'constraints': ['Cannot insert records or create index'
                                    'because of uniqueness constraint'],
                    'info': {
                        'orig': str(e.orig),
                        'pgcode': e.orig.pgcode
                    }
                })
            raise
        except DataError as e:
            raise ValidationError({
                'data': e.message,
                'info': {
                    'orig': [str(e.orig)]
                }})
        except DBAPIError as e:
            if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
                raise ValidationError({
                    'query': ['Query took too long']
                })
            raise
        except Exception as e:
            trans.rollback()
            raise
        finally:
            context['connection'].close()

    def upsert(self, context, data_dict):
        data_dict['connection_url'] = self.write_url
        return upsert(context, data_dict)

    def search(self, context, data_dict):
        data_dict['connection_url'] = self.write_url
        return search(context, data_dict)

    def search_sql(self, context, data_dict):
        sql = toolkit.get_or_bust(data_dict, 'sql')
        data_dict['connection_url'] = self.read_url

        if not is_single_statement(sql):
            raise toolkit.ValidationError({
                'query': ['Query is not a single statement.']
            })
        return search_sql(context, data_dict)

    def resource_exists(self, id):
        resources_sql = sqlalchemy.text(
            u'''SELECT 1 FROM "_table_metadata"
            WHERE name = :id AND alias_of IS NULL''')
        results = self._get_read_engine().execute(resources_sql, id=id)
        res_exists = results.rowcount > 0
        return res_exists

    def resource_id_from_alias(self, alias):
        real_id = None
        resources_sql = sqlalchemy.text(u'''SELECT alias_of FROM "_table_metadata"
                                        WHERE name = :id''')
        results = self._get_read_engine().execute(resources_sql, id=alias)

        res_exists = results.rowcount > 0
        if res_exists:
            real_id = results.fetchone()[0]
        return res_exists, real_id

    # def resource_info(self, id):
    #     pass

    def resource_fields(self, id):
        def _type_lookup(t):
            if t in ['numeric', 'integer']:
                return 'number'
            if t.startswith('timestamp'):
                return "date"
            return "text"

        info = {'schema': {}, 'meta': {}}

        schema_results = None
        meta_results = None
        try:
            schema_sql = sqlalchemy.text(u'''
                SELECT column_name, data_type
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE table_name = :resource_id;
            ''')
            schema_results = self._get_read_engine().execute(
                schema_sql, resource_id=id)
            for row in schema_results.fetchall():
                k = row[0]
                v = row[1]
                if k.startswith('_'):  # Skip internal rows
                    continue
                info['schema'][k] = _type_lookup(v)

            # We need to make sure the resource_id is a valid resource_id
            # before we use it like this, we have done that above.
            meta_sql = sqlalchemy.text(u'''
                SELECT count(_id) FROM "{0}";
            '''.format(id))
            meta_results = self._get_read_engine().execute(
                meta_sql, resource_id=id)
            info['meta']['count'] = meta_results.fetchone()[0]
        finally:
            if schema_results:
                schema_results.close()
            if meta_results:
                meta_results.close()
        return info

    def get_all_ids(self):
        resources_sql = sqlalchemy.text(
            u'''SELECT name FROM "_table_metadata"
            WHERE alias_of IS NULL''')
        query = self._get_read_engine().execute(resources_sql)
        return [q[0] for q in query.fetchall()]

    def create_function(self, *args, **kwargs):
        return create_function(*args, **kwargs)

    def drop_function(self, *args, **kwargs):
        return drop_function(*args, **kwargs)

    def before_fork(self):
        # Called by DatastorePlugin.before_fork. Dispose SQLAlchemy engines
        # to avoid sharing them between parent and child processes.
        _dispose_engines()


def create_function(name, arguments, rettype, definition, or_replace):
    sql = u'''
        CREATE {or_replace} FUNCTION
            {name}({args}) RETURNS {rettype} AS {definition}
            LANGUAGE plpgsql;'''.format(
        or_replace=u'OR REPLACE' if or_replace else u'',
        name=identifier(name),
        args=u', '.join(
            u'{argname} {argtype}'.format(
                argname=identifier(a['argname']),
                argtype=identifier(a['argtype']))
            for a in arguments),
        rettype=identifier(rettype),
        definition=literal_string(definition))

    try:
        _write_engine_execute(sql)
    except ProgrammingError as pe:
        already_exists = (
          u'function "{}" already exists with same argument types'.format(name)
          in pe.args[0])
        key = u'name' if already_exists else u'definition'
        raise ValidationError({key: [_programming_error_summary(pe)]})


def drop_function(name, if_exists):
    sql = u'''
        DROP FUNCTION {if_exists} {name}();
        '''.format(
        if_exists=u'IF EXISTS' if if_exists else u'',
        name=identifier(name))

    try:
        _write_engine_execute(sql)
    except ProgrammingError as pe:
        raise ValidationError({u'name': [_programming_error_summary(pe)]})


def _write_engine_execute(sql):
    connection = get_write_engine().connect()
    # No special meaning for '%' in sql parameter:
    connection = connection.execution_options(no_parameters=True)
    trans = connection.begin()
    try:
        connection.execute(sql)
        trans.commit()
    except Exception:
        trans.rollback()
        raise
    finally:
        connection.close()


def _programming_error_summary(pe):
    u'''
    return the text description of a sqlalchemy DatabaseError
    without the actual SQL included, for raising as a
    ValidationError to send back to API users
    '''
    # first line only, after the '(ProgrammingError)' text
    message = pe.args[0].split('\n')[0].decode('utf8')
    return message.split(u') ', 1)[-1]
