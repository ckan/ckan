import sqlalchemy
from sqlalchemy.exc import ProgrammingError, IntegrityError
from sqlalchemy import text
import ckan.plugins as p
import psycopg2.extras
import json
import datetime
import shlex
from paste.deploy.converters import asbool, aslist

_pg_types = {}
_type_names = set()
_engines = {}

_date_formats = ['%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%d/%m/%Y',
                '%m/%d/%Y',
                '%d-%m-%Y',
                '%m-%d-%Y',
                ]
_pluck = lambda field, arr: [x[field] for x in arr]
INSERT = 'insert'
UPSERT = 'upsert'
UPDATE = 'update'
_methods = [INSERT, UPSERT, UPDATE]


def _strip(input):
    if isinstance(input, basestring):
        return input.strip('"')
    return input


def _get_list(input):
    """Transforms a string or list to a list"""
    if input == None:
        return
    if input == '':
        return []
    return [_strip(x) for x in aslist(input, ',', True)]


def _get_bool(input, default=False):
    if input in [None, '']:
        return default
    return asbool(input)


def _is_valid_field_name(name):
    '''
    Check that field name is valid:
    * can't start with underscore
    * can't contain double quote (")
    '''
    if name.startswith('_') or '"' in name:
        return False
    return True


_is_valid_table_name = _is_valid_field_name


def _validate_int(i, field_name):
    try:
        int(i)
    except ValueError:
        raise p.toolkit.ValidationError({
            'field_name': ['{0} is not an integer'.format(i)]
        })


def _get_engine(context, data_dict):
    'Get either read or write engine.'
    connection_url = data_dict['connection_url']
    engine = _engines.get(connection_url)

    if not engine:
        engine = sqlalchemy.create_engine(connection_url)
        _engines[connection_url] = engine
    return engine


def _cache_types(context):
    if not _pg_types:
        connection = context['connection']
        results = connection.execute(
            'select oid, typname from pg_type;'
        )
        for result in results:
            _pg_types[result[0]] = result[1]
            _type_names.add(result[1])
        if '_json' not in _type_names:
            connection.execute('create type "_json" as (json text, extra text)')
            _pg_types.clear()
            ## redo cache types with json now availiable.
            return _cache_types(context)

        psycopg2.extras.register_composite('_json', connection.connection, True)


def _get_type(context, oid):
    _cache_types(context)
    return _pg_types[oid]


def _guess_type(field):
    'Simple guess type of field, only allowed are integer, numeric and text'
    data_types = set([int, float])
    if isinstance(field, (dict, list)):
        return '_json'
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
    for format in _date_formats:
        try:
            datetime.datetime.strptime(field, format)
            return 'timestamp'
        except ValueError:
            continue
    return 'text'


def _get_fields(context, data_dict):
    fields = []
    all_fields = context['connection'].execute(
        u'select * from "{0}" limit 1'.format(data_dict['resource_id'])
    )
    for field in all_fields.cursor.description:
        if not field[0].startswith('_'):
            fields.append({
                'id': field[0].decode('utf-8'),
                'type': _get_type(context, field[1])
            })
    return fields


def json_get_values(obj, current_list=None):
    if current_list is None:
        current_list = []
    if isinstance(obj, basestring):
        current_list.append(obj)
    if isinstance(obj, list):
        for item in obj:
            json_get_values(item, current_list)
    if isinstance(obj, dict):
        for item in obj.values():
            json_get_values(item, current_list)
    return current_list


def check_fields(context, fields):
    'Check if field types are valid.'
    for field in fields:
        if field.get('type') and not field['type'] in _type_names:
            raise p.toolkit.ValidationError({
                'fields': ['{0} is not a valid field type'.format(field['type'])]
            })
        elif not _is_valid_field_name(field['id']):
            raise p.toolkit.ValidationError({
                'fields': ['{0} is not a valid field name'.format(field['id'])]
            })


def convert(data, type):
    if data is None:
        return None
    if type == '_json':
        return json.loads(data[0])
    if isinstance(data, datetime.datetime):
        return data.isoformat()
    if isinstance(data, (int, float)):
        return data
    return unicode(data)


def create_table(context, data_dict):
    'Create table from combination of fields and first row of data.'

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
                raise p.toolkit.ValidationError({
                    'fields': ['{0} type not guessable'.format(field['id'])]
                })
            field['type'] = _guess_type(records[0][field['id']])

    if records:
        # check record for sanity
        if not isinstance(records[0], dict):
            raise p.toolkit.ValidationError({
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
    sql_fields = u", ".join([u'"{0}" {1}'.format(f['id'], f['type'])
                            for f in fields])

    sql_string = u'create table "{0}" ({1});'.format(
        data_dict['resource_id'],
        sql_fields
    )

    context['connection'].execute(sql_string)


def _get_aliases(context, data_dict):
    res_id = data_dict['resource_id']
    alias_sql = text(u'select name from "_table_metadata" where alias_of = :id')
    results = context['connection'].execute(alias_sql, id=res_id).fetchall()
    return [x[0] for x in results]


def create_alias(context, data_dict):
    aliases = _get_list(data_dict.get('aliases', None))
    if aliases:
        # delete previous aliases
        previous_aliases = _get_aliases(context, data_dict)
        for alias in previous_aliases:
            sql_alias_drop_string = u'drop view "{0}"'.format(alias)
            context['connection'].execute(sql_alias_drop_string)

        for alias in aliases:
            sql_alias_string = u'create view "{alias}" as select * from "{main}"'.format(
                main=data_dict['resource_id'],
                alias=alias
            )
            context['connection'].execute(sql_alias_string)


def create_indexes(context, data_dict):
    indexes = _get_list(data_dict.get('indexes'))
    # primary key is not a real primary key
    # it's just a unique key
    primary_key = _get_list(data_dict.get('primary_key'))

    # index and primary key could be [],
    # which means that indexes should be deleted
    if indexes == None and primary_key == None:
        return

    sql_index_string = u'create {unique} index on "{res_id}" using {method}({fields})'
    sql_index_strings = []
    field_ids = _pluck('id', _get_fields(context, data_dict))

    if indexes != None:
        _drop_indexes(context, data_dict, False)

        for index in indexes:
            fields = _get_list(index)
            for field in fields:
                if field not in field_ids:
                    raise p.toolkit.ValidationError({
                        'index': [('The field {0} is not a valid column name.').format(
                            index)]
                    })
            fields_string = u','.join(['"%s"' % field for field in fields])
            sql_index_strings.append(sql_index_string.format(
                res_id=data_dict['resource_id'], unique='',
                method='btree', fields=fields_string))

        # create index for faster full text search (indexes: gin or gist)
        sql_index_strings.append(sql_index_string.format(
                res_id=data_dict['resource_id'], unique='',
                method='gist', fields='_full_text'))
    if primary_key != None:
        _drop_indexes(context, data_dict, True)

        # create unique index
        for field in primary_key:
            if field not in field_ids:
                raise p.toolkit.ValidationError({
                    'primary_key': [('The field {0} is not a valid column name.').format(
                        field)]
                })
        if primary_key:
            sql_index_strings.append(sql_index_string.format(
                res_id=data_dict['resource_id'], unique='unique',
                method='btree', fields=u','.join(['"%s"' % field for field in primary_key])))

    map(context['connection'].execute, sql_index_strings)


def _drop_indexes(context, data_dict, unique=False):
    sql_drop_index = u'drop index "{0}" cascade'
    sql_get_index_string = u"""
        select
            i.relname as index_name
        from
            pg_class t,
            pg_class i,
            pg_index idx
        where
            t.oid = idx.indrelid
            and i.oid = idx.indexrelid
            and t.relkind = 'r'
            and idx.indisunique = {unique}
            and idx.indisprimary = false
            and t.relname = %s
        """
    sql_stmt = sql_get_index_string.format(
        unique='true' if unique else 'false')
    indexes_to_drop = context['connection'].execute(
        sql_stmt, data_dict['resource_id']).fetchall()
    for index in indexes_to_drop:
        context['connection'].execute(sql_drop_index.format(index[0]))


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
        # check to see if field definition is the same or an
        # extension of current fields
        if num < len(current_fields):
            if field['id'] != current_fields[num]['id']:
                raise p.toolkit.ValidationError({
                    'fields': [('Supplied field "{0}" not '
                              'present or in wrong order').format(field['id'])]
                })
            ## no need to check type as field already defined.
            continue

        if 'type' not in field:
            if not records or field['id'] not in records[0]:
                raise p.toolkit.ValidationError({
                    'fields': ['{0} type not guessable'.format(field['id'])]
                })
            field['type'] = _guess_type(records[0][field['id']])
        new_fields.append(field)

    if records:
        # check record for sanity
        if not isinstance(records[0], dict):
            raise p.toolkit.ValidationError({
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
        sql = 'alter table "{0}" add "{1}" {2}'.format(
            data_dict['resource_id'],
            field['id'],
            field['type'])
        context['connection'].execute(sql)


def insert_data(context, data_dict):
    data_dict['method'] = INSERT
    return upsert_data(context, data_dict)


def upsert_data(context, data_dict):
    '''insert all data from records'''
    if not data_dict.get('records'):
        return

    method = data_dict.get('method', UPSERT)

    if method not in _methods:
        raise p.toolkit.ValidationError({
            'method': [u'{0} is not defined'.format(method)]
        })

    fields = _get_fields(context, data_dict)
    field_names = _pluck('id', fields)
    records = data_dict['records']
    sql_columns = ", ".join(['"%s"' % name for name in field_names]
                            + ['"_full_text"'])

    if method in [UPDATE, UPSERT]:
        unique_keys = _get_unique_key(context, data_dict)
        if len(unique_keys) < 1:
            raise p.toolkit.ValidationError({
                'table': [u'table does not have a key defined']
            })

    if method == INSERT:
        rows = []
        for num, record in enumerate(records):
            _validate_record(record, num, field_names)

            row = []
            for field in fields:
                value = record.get(field['id'])
                if field['type'].lower() == '_json' and value:
                    ## a tuple with an empty second value
                    value = (json.dumps(value), '')
                row.append(value)
            row.append(_to_full_text(fields, record))
            rows.append(row)

        sql_string = u'insert into "{res_id}" ({columns}) values ({values}, to_tsvector(%s));'.format(
            res_id=data_dict['resource_id'],
            columns=sql_columns,
            values=', '.join(['%s' for field in field_names])
        )

        context['connection'].execute(sql_string, rows)

    elif method == UPDATE:
        for num, record in enumerate(records):
            # all key columns have to be defined
            missing_fields = [field for field in unique_keys
                    if field not in record]
            if missing_fields:
                raise p.toolkit.ValidationError({
                    'key': [u'fields "{0}" are missing but needed as key'.format(
                        ', '.join(missing_fields))]
                })
            unique_values = [record[key] for key in unique_keys]

            used_field_names = record.keys()
            used_values = [record[field] for field in used_field_names]
            full_text = _to_full_text(fields, record)

            non_existing_filed_names = [field for field in used_field_names
                if field not in field_names]
            if non_existing_filed_names:
                raise p.toolkit.ValidationError({
                    'fields': [u'fields "{0}" do not exist'.format(
                        ', '.join(missing_fields))]
                })

            sql_string = u'''
                update "{res_id}"
                set ({columns}, "_full_text") = ({values}, to_tsvector(%s))
                where ({primary_key}) = ({primary_value});
            '''.format(
                res_id=data_dict['resource_id'],
                columns=u', '.join([u'"{0}"'.format(field) for field in used_field_names]),
                values=u', '.join(['%s' for _ in used_field_names]),
                primary_key=u','.join([u'"{}"'.format(part) for part in unique_keys]),
                primary_value=u','.join(["%s"] * len(unique_keys))
            )
            results = context['connection'].execute(
                    sql_string, used_values + [full_text] + unique_values)

            # validate that exactly one row has been updated
            if results.rowcount != 1:
                raise p.toolkit.ValidationError({
                    'key': [u'key "{0}" not found'.format(unique_values)]
                })

    elif method == UPSERT:
        # TODO
        pass


def _get_unique_key(context, data_dict):
    sql_get_unique_key = '''
    select
        a.attname as column_names
    from
        pg_class t,
        pg_index idx,
        pg_attribute a
    where
        t.oid = idx.indrelid
        and a.attrelid = t.oid
        and a.attnum = ANY(idx.indkey)
        and t.relkind = 'r'
        and idx.indisunique = true
        and idx.indisprimary = false
        and t.relname = %s
    '''
    key_parts = context['connection'].execute(sql_get_unique_key, data_dict['resource_id'])
    return [x[0] for x in key_parts]


def _validate_record(record, num, field_names):
    # check record for sanity
    if not isinstance(record, dict):
        raise p.toolkit.ValidationError({
            'records': [u'row {0} is not a json object'.format(num)]
        })
    ## check for extra fields in data
    extra_keys = set(record.keys()) - set(field_names)

    if extra_keys:
        raise p.toolkit.ValidationError({
            'records': [u'row {0} has extra keys "{1}"'.format(
                num + 1,
                ', '.join(list(extra_keys))
            )]
        })


def _to_full_text(fields, record):
    full_text = []
    for field in fields:
        value = record.get(field['id'])
        if field['type'].lower() == '_json' and value:
            full_text.extend(json_get_values(value))
        elif field['type'].lower() == 'text' and value:
            full_text.append(value)
    return ' '.join(full_text)


def _where(field_ids, data_dict):
    'Return a SQL WHERE clause from data_dict filters and q'
    filters = data_dict.get('filters', {})

    if not isinstance(filters, dict):
        raise p.toolkit.ValidationError({
            'filters': ['Not a json object']}
        )

    where_clauses = []
    values = []

    for field, value in filters.iteritems():
        if field not in field_ids:
            raise p.toolkit.ValidationError({
                'filters': ['field "{0}" not in table'.format(field)]}
            )
        where_clauses.append(u'"{0}" = %s'.format(field))
        values.append(value)

    # add full-text search where clause
    if data_dict.get('q'):
        where_clauses.append('_full_text @@ query')

    where_clause = ' and '.join(where_clauses)
    if where_clause:
        where_clause = 'where ' + where_clause
    return where_clause, values


def _textsearch_query(data_dict):
    q = data_dict.get('q')
    lang = data_dict.get('lang', 'english')
    if q:
        if (_get_bool(data_dict.get('plain'), True)):
            statement = ", plainto_tsquery('{lang}', '{query}') query"
        else:
            statement = ", to_tsquery('{lang}', '{query}') query"

        rank_column = ', ts_rank(_full_text, query, 32) AS rank'
        return statement.format(lang=lang, query=q), rank_column
    return '', ''


def _sort(context, data_dict, field_ids):
    sort = data_dict.get('sort')
    if not sort:
        if data_dict.get('q'):
            return 'order by rank'
        else:
            return ''

    if isinstance(sort, basestring):
        clauses = sort.split(',')
    elif isinstance(sort, list):
        clauses = sort
    else:
        raise p.toolkit.ValidationError({
            'sort': ['sort is not a list or a string']
        })

    clause_parsed = []

    for clause in clauses:
        clause = clause.encode('utf-8')
        clause_parts = shlex.split(clause)
        if len(clause_parts) == 1:
            field, sort = clause_parts[0], 'asc'
        elif len(clause_parts) == 2:
            field, sort = clause_parts
        else:
            raise p.toolkit.ValidationError({
                'sort': ['not valid syntax for sort clause']
            })
        field, sort = unicode(field, 'utf-8'), unicode(sort, 'utf-8')

        if field not in field_ids:
            raise p.toolkit.ValidationError({
                'sort': [u'field {0} not it table'.format(
                    unicode(field, 'utf-8'))]
            })
        if sort.lower() not in ('asc', 'desc'):
            raise p.toolkit.ValidationError({
                'sort': ['sorting can only be asc or desc']
            })
        clause_parsed.append(u'"{0}" {1}'.format(
            field, sort)
        )

    if clause_parsed:
        return "order by " + ", ".join(clause_parsed)


def delete_data(context, data_dict):
    fields = _get_fields(context, data_dict)
    field_ids = set([field['id'] for field in fields])
    where_clause, where_values = _where(field_ids, data_dict)

    context['connection'].execute(
        u'delete from "{0}" {1}'.format(
            data_dict['resource_id'],
            where_clause
        ),
        where_values
    )


def search_data(context, data_dict):
    all_fields = _get_fields(context, data_dict)
    all_field_ids = _pluck('id', all_fields)
    all_field_ids.insert(0, '_id')

    fields = data_dict.get('fields')

    if fields:
        field_ids = _get_list(fields)

        for field in field_ids:
            if not field in all_field_ids:
                raise p.toolkit.ValidationError({
                    'fields': [u'field "{0}" not in table'.format(field)]}
                )
    else:
        field_ids = all_field_ids

    select_columns = ', '.join([u'"{0}"'.format(field_id)
                                for field_id in field_ids])
    ts_query, rank_column = _textsearch_query(data_dict)
    where_clause, where_values = _where(all_field_ids, data_dict)
    limit = data_dict.get('limit', 100)
    offset = data_dict.get('offset', 0)

    _validate_int(limit, 'limit')
    _validate_int(offset, 'offset')

    sort = _sort(context, data_dict, field_ids)

    sql_string = u'''select {select}, count(*) over() as "_full_count" {rank}
                    from "{resource}" {ts_query}
                    {where} {sort} limit {limit} offset {offset}'''.format(
            select=select_columns,
            rank=rank_column,
            resource=data_dict['resource_id'],
            ts_query=ts_query,
            where=where_clause,
            sort=sort, limit=limit, offset=offset)
    results = context['connection'].execute(sql_string, where_values)
    return format_results(context, results, data_dict)


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
    return data_dict


def _is_single_statement(sql):
    return not ';' in sql.strip(';')


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
    '''
    engine = _get_engine(context, data_dict)
    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', 60000)
    _cache_types(context)

    # close connection at all cost.
    try:
        # check if table already existes
        trans = context['connection'].begin()
        context['connection'].execute(
            u'set local statement_timeout to {0}'.format(timeout))
        result = context['connection'].execute(
            u'select * from pg_tables where tablename = %s',
             data_dict['resource_id']
        ).fetchone()
        if not result:
            create_table(context, data_dict)
        else:
            alter_table(context, data_dict)
        insert_data(context, data_dict)
        create_indexes(context, data_dict)
        create_alias(context, data_dict)
        trans.commit()
        return data_dict
    except IntegrityError, e:
        if ('duplicate key value violates unique constraint' in str(e)
                or 'could not create unique index' in str(e)):
            raise p.toolkit.ValidationError({
                'constraints': ['Cannot insert records because of uniqueness constraint in index'],
                'info': {
                    'details': str(e)
                }
            })
        else:
            raise
    except Exception, e:
        if 'due to statement timeout' in str(e):
            raise p.toolkit.ValidationError({
                'query': ['Query took too long']
            })
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
    engine = _get_engine(context, data_dict)
    context['connection'] = engine.connect()

    # check if table already existes
    trans = context['connection'].begin()
    upsert_data(context, data_dict)
    trans.commit()
    return data_dict


def delete(context, data_dict):
    engine = _get_engine(context, data_dict)
    context['connection'] = engine.connect()
    _cache_types(context)

    try:
        # check if table exists
        trans = context['connection'].begin()
        result = context['connection'].execute(
            u'select 1 from pg_tables where tablename = %s',
             data_dict['resource_id']
        ).fetchone()
        if not result:
            raise p.toolkit.ValidationError({
                'resource_id': [u'table for resource {0} does not exist'.format(
                    data_dict['resource_id'])]
            })
        if not 'filters' in data_dict:
            context['connection'].execute(
                u'drop table "{0}" cascade'.format(data_dict['resource_id'])
            )
        else:
            delete_data(context, data_dict)

        trans.commit()
        return data_dict
    except Exception:
        trans.rollback()
        raise
    finally:
        context['connection'].close()


def search(context, data_dict):
    engine = _get_engine(context, data_dict)
    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', 60000)
    _cache_types(context)

    try:
        # check if table exists
        context['connection'].execute(
            u'set local statement_timeout to {0}'.format(timeout))
        id = data_dict['resource_id']
        result = context['connection'].execute(
            u"(select 1 from pg_tables where tablename = '{0}') union"
             u"(select 1 from pg_views where viewname = '{0}')".format(id)
        ).fetchone()
        if not result:
            raise p.toolkit.ValidationError({
                'resource_id': [u'table for resource {0} does not exist'.format(
                    data_dict['resource_id'])]
            })
        return search_data(context, data_dict)
    except Exception, e:
        if 'due to statement timeout' in str(e):
            raise p.toolkit.ValidationError({
                'query': ['Search took too long']
            })
        raise
    finally:
        context['connection'].close()


def search_sql(context, data_dict):
    engine = _get_engine(context, data_dict)
    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', 60000)
    _cache_types(context)

    try:
        context['connection'].execute(
            u'set local statement_timeout to {0}'.format(timeout))
        results = context['connection'].execute(
            data_dict['sql']
        )
        return format_results(context, results, data_dict)

    except ProgrammingError, e:
        raise p.toolkit.ValidationError({
         'query': [str(e)],
         'info': {
            'statement': [e.statement],
            'params': [e.params],
            'orig': [str(e.orig)]
         }
        })
    except Exception, e:
        if 'due to statement timeout' in str(e):
            raise p.toolkit.ValidationError({
                'query': ['Search took too long']
            })
        raise
    finally:
        context['connection'].close()
