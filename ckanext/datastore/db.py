import json
import datetime
import os
import urllib
import urllib2
import urlparse
import logging
import pprint
import copy
import hashlib

import pylons
import distutils.version
import sqlalchemy
from sqlalchemy.exc import (ProgrammingError, IntegrityError,
                            DBAPIError, DataError)
import psycopg2.extras
import ckan.lib.cli as cli
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
import ckanext.datastore.interfaces as interfaces
import ckanext.datastore.helpers as datastore_helpers
from ckan.common import OrderedDict

log = logging.getLogger(__name__)

if not os.environ.get('DATASTORE_LOAD'):
    ValidationError = toolkit.ValidationError
else:
    log.warn("Running datastore without CKAN")

    class ValidationError(Exception):
        def __init__(self, error_dict):
            pprint.pprint(error_dict)

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


class InvalidDataError(Exception):
    """Exception that's raised if you try to add invalid data to the datastore.

    For example if you have a column with type "numeric" and then you try to
    add a non-numeric value like "foo" to it, this exception should be raised.

    """
    pass


def _pluck(field, arr):
    return [x[field] for x in arr]


def _is_valid_field_name(name):
    '''
    Check that field name is valid:
    * can't start or end with whitespace characters
    * can't start with underscore
    * can't contain double quote (")
    * can't be empty
    '''
    return (name and name == name.strip() and not name.startswith('_')
            and not '"' in name)


def _is_valid_table_name(name):
    if '%' in name:
        return False
    return _is_valid_field_name(name)


def _get_engine(data_dict):
    '''Get either read or write engine.'''
    connection_url = data_dict['connection_url']
    engine = _engines.get(connection_url)

    if not engine:
        import pylons
        extras = {'url': connection_url}
        engine = sqlalchemy.engine_from_config(pylons.config,
                                               'ckan.datastore.sqlalchemy.',
                                               **extras)
        _engines[connection_url] = engine
    return engine


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

            log.info("Create nested type. Native JSON: {0}".format(
                native_json))

            data_dict = {
                'connection_url': pylons.config['ckan.datastore.write_url']}
            engine = _get_engine(data_dict)
            with engine.begin() as connection:
                connection.execute(
                    'CREATE TYPE "nested" AS (json {0}, extra text)'.format(
                        'json' if native_json else 'text'))
            _pg_types.clear()

            ## redo cache types with json now available.
            return _cache_types(context)

        psycopg2.extras.register_composite('nested',
                                           connection.connection,
                                           True)


def _pg_version_is_at_least(connection, version):
    try:
        v = distutils.version.LooseVersion(version)
        pg_version = connection.execute('select version();').fetchone()
        pg_version_number = pg_version[0].split()[1]
        pv = distutils.version.LooseVersion(pg_version_number)
        return v <= pv
    except ValueError:
        return False


def _is_valid_pg_type(context, type_name):
    if type_name in _type_names:
        return True
    else:
        connection = context['connection']
        try:
            connection.execute('SELECT %s::regtype', type_name)
        except ProgrammingError, e:
            if e.orig.pgcode in [_PG_ERR_CODE['undefined_object'],
                                 _PG_ERR_CODE['syntax_error']]:
                return False
            raise
        else:
            return True


def _get_type(context, oid):
    _cache_types(context)
    return _pg_types[oid]


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

    ##try iso dates
    for format in _DATE_FORMATS:
        try:
            datetime.datetime.strptime(field, format)
            return 'timestamp'
        except (ValueError, TypeError):
            continue
    return 'text'


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


def _get_fields_types(context, data_dict):
    all_fields = _get_fields(context, data_dict)
    all_fields.insert(0, {'id': '_id', 'type': 'int'})
    field_types = OrderedDict([(f['id'], f['type']) for f in all_fields])
    return field_types


def json_get_values(obj, current_list=None):
    if current_list is None:
        current_list = []
    if isinstance(obj, list) or isinstance(obj, tuple):
        for item in obj:
            json_get_values(item, current_list)
    elif isinstance(obj, dict):
        json_get_values(obj.items(), current_list)
    elif obj:
        current_list.append(str(obj))
    return current_list


def check_fields(context, fields):
    '''Check if field types are valid.'''
    for field in fields:
        if field.get('type') and not _is_valid_pg_type(context, field['type']):
            raise ValidationError({
                'fields': ['"{0}" is not a valid field type'.format(
                    field['type'])]
            })
        elif not _is_valid_field_name(field['id']):
            raise ValidationError({
                'fields': ['"{0}" is not a valid field name'.format(
                    field['id'])]
            })


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
        return unicode(data, 'utf-8')
    if isinstance(data, datetime.datetime):
        return data.isoformat()
    if isinstance(data, (int, float)):
        return data
    return unicode(data)


def create_table(context, data_dict):
    '''Create table from combination of fields and first row of data.'''

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

    # if type is field is not given try and guess or throw an error
    for field in supplied_fields:
        if 'type' not in field:
            if not records or field['id'] not in records[0]:
                raise ValidationError({
                    'fields': ['"{0}" type not guessable'.format(field['id'])]
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
            if not field_id in field_ids:
                extra_fields.append({
                    'id': field_id,
                    'type': _guess_type(records[0][field_id])
                })

    fields = datastore_fields + supplied_fields + extra_fields
    sql_fields = u", ".join([u'"{0}" {1}'.format(
        f['id'], f['type']) for f in fields])

    sql_string = u'CREATE TABLE "{0}" ({1});'.format(
        data_dict['resource_id'],
        sql_fields
    )

    context['connection'].execute(sql_string.replace('%', '%%'))


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
        except DBAPIError, e:
            if e.orig.pgcode in [_PG_ERR_CODE['duplicate_table'],
                                 _PG_ERR_CODE['duplicate_alias']]:
                raise ValidationError({
                    'alias': ['"{0}" already exists'.format(alias)]
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
                        ('The field "{0}" is not a valid column name.').format(
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


def _build_fts_indexes(connection, data_dict, sql_index_str_method, fields):
    fts_indexes = []
    resource_id = data_dict['resource_id']
    # FIXME: This is repeated on the plugin.py, we should keep it DRY
    default_fts_lang = pylons.config.get('ckan.datastore.default_fts_lang')
    if default_fts_lang is None:
        default_fts_lang = u'english'
    fts_lang = data_dict.get('lang', default_fts_lang)

    # create full-text search indexes
    to_tsvector = lambda x: u"to_tsvector('{0}', {1})".format(fts_lang, x)
    cast_as_text = lambda x: u'cast("{0}" AS text)'.format(x)
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


def _generate_index_name(resource_id, field):
    value = (resource_id + field).encode('utf-8')
    return hashlib.sha1(value).hexdigest()


def _get_fts_index_method():
    method = pylons.config.get('ckan.datastore.default_fts_index_method')
    return method or 'gist'


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


def alter_table(context, data_dict):
    '''alter table from combination of fields and first row of data
    return: all fields of the resource table'''
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
                    'fields': [('Supplied field "{0}" not '
                                'present or in wrong order').format(
                        field['id'])]
                })
            ## no need to check type as field already defined.
            continue

        if 'type' not in field:
            if not records or field['id'] not in records[0]:
                raise ValidationError({
                    'fields': ['"{0}" type not guessable'.format(field['id'])]
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
            if not field_id in field_ids:
                new_fields.append({
                    'id': field_id,
                    'type': _guess_type(records[0][field_id])
                })

    for field in new_fields:
        sql = 'ALTER TABLE "{0}" ADD "{1}" {2}'.format(
            data_dict['resource_id'],
            field['id'],
            field['type'])
        context['connection'].execute(sql.replace('%', '%%'))


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
    sql_columns = ", ".join(['"%s"' % name.replace(
        '%', '%%') for name in field_names] + ['"_full_text"'])

    if method == _INSERT:
        rows = []
        for num, record in enumerate(records):
            _validate_record(record, num, field_names)

            row = []
            for field in fields:
                value = record.get(field['id'])
                if value and field['type'].lower() == 'nested':
                    ## a tuple with an empty second value
                    value = (json.dumps(value), '')
                row.append(value)
            row.append(_to_full_text(fields, record))
            rows.append(row)

        sql_string = u'''INSERT INTO "{res_id}" ({columns})
            VALUES ({values}, to_tsvector(%s));'''.format(
            res_id=data_dict['resource_id'],
            columns=sql_columns,
            values=', '.join(['%s' for field in field_names])
        )

        try:
            context['connection'].execute(sql_string, rows)
        except sqlalchemy.exc.DataError as err:
            raise InvalidDataError(
                toolkit._("The data was invalid (for example: a numeric value "
                          "is out of range or was inserted into a text field)."
                          ))

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
                    ## a tuple with an empty second value
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

            full_text = _to_full_text(fields, record)

            if method == _UPDATE:
                sql_string = u'''
                    UPDATE "{res_id}"
                    SET ({columns}, "_full_text") = ({values}, to_tsvector(%s))
                    WHERE ({primary_key}) = ({primary_value});
                '''.format(
                    res_id=data_dict['resource_id'],
                    columns=u', '.join(
                        [u'"{0}"'.format(field)
                         for field in used_field_names]),
                    values=u', '.join(
                        ['%s' for _ in used_field_names]),
                    primary_key=u','.join(
                        [u'"{0}"'.format(part) for part in unique_keys]),
                    primary_value=u','.join(["%s"] * len(unique_keys))
                )
                results = context['connection'].execute(
                    sql_string, used_values + [full_text] + unique_values)

                # validate that exactly one row has been updated
                if results.rowcount != 1:
                    raise ValidationError({
                        'key': [u'key "{0}" not found'.format(unique_values)]
                    })

            elif method == _UPSERT:
                sql_string = u'''
                    UPDATE "{res_id}"
                    SET ({columns}, "_full_text") = ({values}, to_tsvector(%s))
                    WHERE ({primary_key}) = ({primary_value});
                    INSERT INTO "{res_id}" ({columns}, "_full_text")
                           SELECT {values}, to_tsvector(%s)
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
                context['connection'].execute(
                    sql_string,
                    (used_values + [full_text] + unique_values) * 2)


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


def _validate_record(record, num, field_names):
    # check record for sanity
    if not isinstance(record, dict):
        raise ValidationError({
            'records': [u'row "{0}" is not a json object'.format(num)]
        })
    ## check for extra fields in data
    extra_keys = set(record.keys()) - set(field_names)

    if extra_keys:
        raise ValidationError({
            'records': [u'row "{0}" has extra keys "{1}"'.format(
                num + 1,
                ', '.join(list(extra_keys))
            )]
        })


def _to_full_text(fields, record):
    full_text = []
    ft_types = ['int8', 'int4', 'int2', 'float4', 'float8', 'date', 'time',
                'timetz', 'timestamp', 'numeric', 'text']
    for field in fields:
        value = record.get(field['id'])
        if not value:
            continue

        if field['type'].lower() in ft_types and unicode(value):
            full_text.append(unicode(value))
        else:
            full_text.extend(json_get_values(value))
    return ' '.join(set(full_text))


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


def delete_data(context, data_dict):
    validate(context, data_dict)
    fields_types = _get_fields_types(context, data_dict)

    query_dict = {
        'where': []
    }

    for plugin in p.PluginImplementations(interfaces.IDatastore):
        query_dict = plugin.datastore_delete(context, data_dict,
                                             fields_types, query_dict)

    where_clause, where_values = _where(query_dict['where'])
    sql_string = u'DELETE FROM "{0}" {1}'.format(
        data_dict['resource_id'],
        where_clause
    )

    _execute_single_statement(context, sql_string, where_values)


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

    for plugin in p.PluginImplementations(interfaces.IDatastore):
        data_dict_copy = plugin.datastore_validate(context,
                                                   data_dict_copy,
                                                   fields_types)

    # Remove default elements in data_dict
    del data_dict_copy['connection_url']
    del data_dict_copy['resource_id']
    data_dict_copy.pop('id', None)

    for key, values in data_dict_copy.iteritems():
        if not values:
            continue
        if isinstance(values, basestring):
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

    sql_string = u'''SELECT {distinct} {select}
                    FROM "{resource}" {ts_query}
                    {where} {sort} LIMIT {limit} OFFSET {offset}'''.format(
        distinct=distinct,
        select=select_columns,
        resource=resource_id,
        ts_query=ts_query,
        where=where_clause,
        sort=sort_clause,
        limit=limit,
        offset=offset)

    results = _execute_single_statement(context, sql_string, where_values)

    _insert_links(data_dict, limit, offset)
    return format_results(context, results, data_dict)


def _execute_single_statement(context, sql_string, where_values):
    if not datastore_helpers.is_single_statement(sql_string):
        raise ValidationError({
            'query': ['Query is not a single statement.']
        })

    results = context['connection'].execute(sql_string, [where_values])

    return results


def format_results(context, results, data_dict):
    result_fields = []
    for field in results.cursor.description:
        result_fields.append({
            'id': field[0].decode('utf-8'),
            'type': _get_type(context, field[1])
        })
    if len(result_fields) and result_fields[-1]['id'] == '_full_count':
        result_fields.pop()  # remove _full_count

    records = []
    for row in results:
        converted_row = {}
        if '_full_count' in row:
            data_dict['total'] = row['_full_count']
        for field in result_fields:
            converted_row[field['id']] = convert(row[field['id']],
                                                 field['type'])
        records.append(converted_row)
    data_dict['records'] = records
    data_dict['fields'] = result_fields

    return _unrename_json_field(data_dict)


def create(context, data_dict):
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

    :raises InvalidDataError: if there is an invalid value in the given data

    '''
    engine = _get_engine(data_dict)
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
        else:
            alter_table(context, data_dict)
        insert_data(context, data_dict)
        create_indexes(context, data_dict)
        create_alias(context, data_dict)
        if data_dict.get('private'):
            _change_privilege(context, data_dict, 'REVOKE')
        trans.commit()
        return _unrename_json_field(data_dict)
    except IntegrityError, e:
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
    except DataError, e:
        raise ValidationError({
            'data': e.message,
            'info': {
                'orig': [str(e.orig)]
            }})
    except DBAPIError, e:
        if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
            raise ValidationError({
                'query': ['Query took too long']
            })
        raise
    except Exception, e:
        trans.rollback()
        raise
    finally:
        context['connection'].close()


def upsert(context, data_dict):
    '''
    This method combines upsert insert and update on the datastore. The method
    that will be used is defined in the mehtod variable.

    Any error results in total failure! For now pass back the actual error.
    Should be transactional.
    '''
    engine = _get_engine(data_dict)
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
    except IntegrityError, e:
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
    except DataError, e:
        raise ValidationError({
            'data': e.message,
            'info': {
                'orig': [str(e.orig)]
            }})
    except DBAPIError, e:
        if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
            raise ValidationError({
                'query': ['Query took too long']
            })
        raise
    except Exception, e:
        trans.rollback()
        raise
    finally:
        context['connection'].close()


def delete(context, data_dict):
    engine = _get_engine(data_dict)
    context['connection'] = engine.connect()
    _cache_types(context)

    trans = context['connection'].begin()
    try:
        # check if table exists
        if not 'filters' in data_dict:
            context['connection'].execute(
                u'DROP TABLE "{0}" CASCADE'.format(data_dict['resource_id'])
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


def search(context, data_dict):
    engine = _get_engine(data_dict)
    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', _TIMEOUT)
    _cache_types(context)

    try:
        context['connection'].execute(
            u'SET LOCAL statement_timeout TO {0}'.format(timeout))
        return search_data(context, data_dict)
    except DBAPIError, e:
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
    engine = _get_engine(data_dict)
    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', _TIMEOUT)
    _cache_types(context)

    sql = data_dict['sql'].replace('%', '%%')

    try:

        context['connection'].execute(
            u'SET LOCAL statement_timeout TO {0}'.format(timeout))

        table_names = datastore_helpers.get_table_names_from_sql(context, sql)
        log.debug('Tables involved in input SQL: {0}'.format(table_names))

        system_tables = [t for t in table_names if t.startswith('pg_')]
        if len(system_tables):
            raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to access system tables']
            })

        results = context['connection'].execute(sql)

        return format_results(context, results, data_dict)

    except ProgrammingError, e:
        if e.orig.pgcode == _PG_ERR_CODE['permission_denied']:
            raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to read resource.']
            })

        def _remove_explain(msg):
            return (msg.replace('EXPLAIN (FORMAT JSON) ', '')
                       .replace('EXPLAIN ', ''))

        raise ValidationError({
            'query': [_remove_explain(str(e))],
            'info': {
                'statement': [_remove_explain(e.statement)],
                'params': [e.params],
                'orig': [_remove_explain(str(e.orig))]
            }
        })
    except DBAPIError, e:
        if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
            raise ValidationError({
                'query': ['Query took too long']
            })
        raise
    finally:
        context['connection'].close()


def _get_read_only_user(data_dict):
    parsed = cli.parse_db_config('ckan.datastore.read_url')
    return parsed['db_user']


def _change_privilege(context, data_dict, what):
    ''' We need a transaction for this code to work '''
    read_only_user = _get_read_only_user(data_dict)
    if what == 'REVOKE':
        sql = u'REVOKE SELECT ON TABLE "{0}" FROM "{1}"'.format(
            data_dict['resource_id'],
            read_only_user)
    elif what == 'GRANT':
        sql = u'GRANT SELECT ON TABLE "{0}" TO "{1}"'.format(
            data_dict['resource_id'],
            read_only_user)
    else:
        raise ValidationError({
            'privileges': 'Can only GRANT or REVOKE but not {0}'.format(what)})
    try:
        context['connection'].execute(sql)
    except ProgrammingError, e:
        log.critical("Error making resource private. {0}".format(e.message))
        raise ValidationError({
            'privileges': [u'cannot make "{0}" private'.format(
                           data_dict['resource_id'])],
            'info': {
                'orig': str(e.orig),
                'pgcode': e.orig.pgcode
            }
        })


def make_private(context, data_dict):
    log.info('Making resource {0} private'.format(
        data_dict['resource_id']))
    engine = _get_engine(data_dict)
    context['connection'] = engine.connect()
    trans = context['connection'].begin()
    try:
        _change_privilege(context, data_dict, 'REVOKE')
        trans.commit()
    finally:
        context['connection'].close()


def make_public(context, data_dict):
    log.info('Making resource {0} public'.format(
        data_dict['resource_id']))
    engine = _get_engine(data_dict)
    context['connection'] = engine.connect()
    trans = context['connection'].begin()
    try:
        _change_privilege(context, data_dict, 'GRANT')
        trans.commit()
    finally:
        context['connection'].close()


def get_all_resources_ids_in_datastore():
    read_url = pylons.config.get('ckan.datastore.read_url')
    write_url = pylons.config.get('ckan.datastore.write_url')
    data_dict = {
        'connection_url': read_url or write_url
    }
    resources_sql = sqlalchemy.text(u'''SELECT name FROM "_table_metadata"
                                        WHERE alias_of IS NULL''')
    query = _get_engine(data_dict).execute(resources_sql)
    return [q[0] for q in query.fetchall()]
