import sqlalchemy
import ckan.plugins as p
import json
import datetime

_pg_types = {}
_type_names = set()
_engines = {}

_iso_formats = ['%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S']


def _is_valid_field_name(name):
    '''
    Check that field name is valid:
    * can't start with underscore
    * can't contain double quote (")
    '''
    if name.startswith('_') or '"' in name:
        return False
    return True


def _validate_int(i, field_name):
    try:
        int(i)
    except ValueError:
        raise p.toolkit.ValidationError({
            'field_name': '{} is not an integer'.format(i)
        })


def _get_engine(context, data_dict):
    'Get either read or write engine.'
    connection_url = data_dict['connection_url']
    engine = _engines.get(connection_url)

    if not engine:
        engine = sqlalchemy.create_engine(connection_url, echo=True)
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


def _get_type(context, oid):
    _cache_types(context)
    return _pg_types[oid]


def _guess_type(field):
    'Simple guess type of field, only allowed are integer, numeric and text'
    data_types = set([int, float])

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
    for format in _iso_formats:
        try:
            datetime.datetime.strptime(field, format)
            return 'timestamp'
        except ValueError:
            continue
    return 'text'


def _get_fields(context, data_dict):
    fields = []
    all_fields = context['connection'].execute(
        'select * from "{0}" limit 1'.format(data_dict['resource_id'])
    )
    for field in all_fields.cursor.description:
        if not field[0].startswith('_'):
            fields.append({
                'id': field[0],
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
        for item in dict.values():
            json_get_values(item, current_list)
    return current_list


def check_fields(context, fields):
    'Check if field types are valid.'
    _cache_types(context)
    for field in fields:
        if field.get('type') and not field['type'] in _type_names:
            raise p.toolkit.ValidationError({
                'fields': '{0} is not a valid field type'.format(field['type'])
            })
        elif not _is_valid_field_name(field['id']):
            raise p.toolkit.ValidationError({
                'fields': '{0} is not a valid field name'.format(field['id'])
            })


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
    field_ids = [field['id'] for field in data_dict.get('fields', [])]
    records = data_dict.get('records')

    # if type is field is not given try and guess or throw an error
    for field in supplied_fields:
        if 'type' not in field:
            if not records or field['id'] not in records[0]:
                raise p.toolkit.ValidationError({
                    'fields': '{} type not guessable'.format(field['id'])
                })
            field['type'] = _guess_type(records[0][field['id']])

    if records:
        # check record for sanity
        if not isinstance(records[0], dict):
            raise p.toolkit.ValidationError({
                'records': 'The first row is not a json object'
            })
        supplied_field_ids = records[0].keys()
        for field_id in supplied_field_ids:
            if not field_id in field_ids:
                extra_fields.append({
                    'id': field_id,
                    'type': _guess_type(records[0][field_id])
                })

    fields = datastore_fields + supplied_fields + extra_fields
    sql_fields = ", ".join(['"{0}" {1}'.format(f['id'], f['type'])
                            for f in fields])

    sql_string = 'create table "{0}" ({1});'.format(
        data_dict['resource_id'],
        sql_fields
    )

    context['connection'].execute(sql_string)


def alter_table(context, data_dict):
    '''alter table from combination of fields and first row of data'''
    supplied_fields = data_dict.get('fields', [])
    current_fields = _get_fields(context, data_dict)
    if not supplied_fields:
        supplied_fields = current_fields
    check_fields(context, supplied_fields)
    field_ids = [field['id'] for field in supplied_fields]
    records = data_dict.get('records')
    new_fields = []

    for num, field in enumerate(supplied_fields):
        # check to see if field definition is the same or an
        # extension of current fields
        if num < len(current_fields):
            if field['id'] != current_fields[num]['id']:
                raise p.toolkit.ValidationError({
                    'fields': ('Supplied field "{}" not '
                              'present or in wrong order').format(field['id'])
                })
            ## no need to check type as field already defined.
            continue

        if 'type' not in field:
            if not records or field['id'] not in records[0]:
                raise p.toolkit.ValidationError({
                    'fields': '{} type not guessable'.format(field['id'])
                })
            field['type'] = _guess_type(records[0][field['id']])
        new_fields.append(field)

    if records:
        # check record for sanity
        if not isinstance(records[0], dict):
            raise p.toolkit.ValidationError({
                'records': 'The first row is not a json object'
            })
        supplied_field_ids = records[0].keys()
        for field_id in supplied_field_ids:
            if not field_id in field_ids:
                new_fields.append({
                    'id': field_id,
                    'type': _guess_type(records[0][field_id])
                })

    for field in new_fields:
        sql = 'alter table "{}" add "{}" {}'.format(
            data_dict['resource_id'],
            field['id'],
            field['type'])
        context['connection'].execute(sql)


def insert_data(context, data_dict):
    '''insert all data from records'''
    if not data_dict.get('records'):
        return

    fields = _get_fields(context, data_dict)
    field_names = [field['id'] for field in fields] + ['_full_text']
    sql_columns = ", ".join(['"%s"' % name for name in field_names])

    rows = []

    ## clean up and validate data
    for num, record in enumerate(data_dict['records']):

        # check record for sanity
        if not isinstance(record, dict):
            raise p.toolkit.ValidationError({
                'records': 'row {} is not a json object'.format(num)
            })
        ## check for extra fields in data
        extra_keys = set(record.keys()) - set(field_names)
        if extra_keys:
            raise p.toolkit.ValidationError({
                'records': 'row {} has extra keys "{}"'.format(
                    num,
                    ', '.join(list(extra_keys))
                )
            })

        full_text = []
        row = []
        for field in fields:
            value = record.get(field['id'])
            if isinstance(value, (dict, list)):
                full_text.extend(json_get_values(value))
                value = json.dumps(value)
            elif field['type'].lower() == 'text' and value:
                full_text.append(value)
            row.append(value)

        row.append(' '.join(full_text))
        rows.append(row)

    sql_string = 'insert into "{0}" ({1}) values ({2});'.format(
        data_dict['resource_id'],
        sql_columns,
        ', '.join(['%s' for field in field_names])
    )

    context['connection'].execute(sql_string, rows)


def _where(field_ids, data_dict):
    'Return a SQL WHERE clause from data_dict filters and q'
    filters = data_dict.get('filters', {})

    if not isinstance(filters, dict):
        raise p.toolkit.ValidationError({
            'filters': 'Not a json object'}
        )

    where_clauses = []
    values = []

    for field, value in filters.iteritems():
        if field not in field_ids:
            raise p.toolkit.ValidationError({
                'filters': 'field "{}" not in table'}
            )
        where_clauses.append('"{}" = %s'.format(field))
        values.append(value)

    q = data_dict.get('q')
    if q:
        where_clauses.append('_full_text @@ to_tsquery(%s)'.format(q))
        values.append(q)

    where_clause = ' and '.join(where_clauses)
    if where_clause:
        where_clause = 'where ' + where_clause
    return where_clause, values


def delete_data(context, data_dict):
    fields = _get_fields(context, data_dict)
    field_ids = set([field['id'] for field in fields])
    where_clause, where_values = _where(field_ids, data_dict)

    context['connection'].execute(
        'delete from "{}" {}'.format(
            data_dict['resource_id'],
            where_clause
        ),
        where_values
    )


def search_data(context, data_dict):
    all_fields = _get_fields(context, data_dict)
    all_field_ids = set([field['id'] for field in all_fields])

    fields = data_dict.get('fields')

    if fields:
        check_fields(context, fields)
        field_ids = set([field['id'] for field in fields])

        for field in field_ids:
            if not field in all_field_ids:
                raise p.toolkit.ValidationError({
                    'fields': 'field "{}" not in table'.format(field)}
                )
    else:
        fields = all_fields
        field_ids = all_field_ids

    select_columns = ', '.join(field_ids)
    where_clause, where_values = _where(all_field_ids, data_dict)
    limit = data_dict.get('limit', 100)
    offset = data_dict.get('offset', 0)

    _validate_int(limit, 'limit')
    _validate_int(offset, 'offset')

    if data_dict.get('sort'):
        sort = 'order by {}'.format(data_dict['sort'])
    else:
        sort = ''

    sql_string = '''select {}, count(*) over() as full_count
                    from "{}" {} {} limit {} offset {}'''\
        .format(select_columns, data_dict['resource_id'], where_clause,
                sort, limit, offset)
    results = context['connection'].execute(sql_string, where_values)
    results = [r for r in results]

    if results:
        data_dict['total'] = results[0]['full_count']
    else:
        data_dict['total'] = 0

    records = [(dict((f, r[f]) for f in field_ids)) for r in results]
    data_dict['records'] = records

    return data_dict


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

    # close connection at all cost.
    try:
        # check if table already existes
        trans = context['connection'].begin()
        result = context['connection'].execute(
            'select * from pg_tables where tablename = %s',
             data_dict['resource_id']
        ).fetchone()
        if not result:
            create_table(context, data_dict)
        else:
            alter_table(context, data_dict)
        insert_data(context, data_dict)
        trans.commit()
        return data_dict
    except:
        trans.rollback()
        raise
    finally:
        context['connection'].close()


def delete(context, data_dict):
    engine = _get_engine(context, data_dict)
    context['connection'] = engine.connect()

    try:
        # check if table existes
        trans = context['connection'].begin()
        result = context['connection'].execute(
            'select * from pg_tables where tablename = %s',
             data_dict['resource_id']
        ).fetchone()
        if not result:
            raise p.toolkit.ValidationError({
                'resource_id': 'table for resource {0} does not exist'.format(
                    data_dict['resource_id'])
            })
        if not 'filters' in data_dict:
            context['connection'].execute(
                'drop table "{}"'.format(data_dict['resource_id'])
            )
        else:
            delete_data(context, data_dict)

        trans.commit()
        return data_dict
    except:
        trans.rollback()
        raise
    finally:
        context['connection'].close()


def search(context, data_dict):
    engine = _get_engine(context, data_dict)
    context['connection'] = engine.connect()

    try:
        # check if table existes
        result = context['connection'].execute(
            'select * from pg_tables where tablename = %s',
             data_dict['resource_id']
        ).fetchone()
        if not result:
            raise p.toolkit.ValidationError({
                'resource_id': 'table for resource {0} does not exist'.format(
                    data_dict['resource_id'])
            })
        return search_data(context, data_dict)
    finally:
        context['connection'].close()
