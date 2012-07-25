import sqlalchemy
import ckan.plugins as p

_pg_types = {}
_type_names = set()
_engines = {}


def _is_valid_field_name(name):
    '''
    Check that field name is valid:
    * can't start with underscore
    * can't contain double quote (")
    '''
    if name.startswith('_') or '"' in name:
        return False
    return True


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
    else:
        return 'text'


def _get_fields(context, data_dict):
    fields = []
    all_fields = context['connection'].execute(
        'select * from "{0}" limit 1'.format(data_dict['resource_id'])
    )
    for field in all_fields.cursor.description:
        if not field[0].startswith('_'):
            fields.append({
                'name': field[0],
                'type': _get_type(context, field[1])
            })
    return fields


def check_fields(context, fields):
    'Check if field types are valid.'
    _cache_types(context)
    for field in fields:
        if not field['type'] in _type_names:
            raise p.toolkit.ValidationError({
                'fields': '{0} is not a valid field type'.format(field['type'])
            })
        elif not _is_valid_field_name(field['id']):
            raise p.toolkit.ValidationError({
                'fields': '{0} is not a valid field name'.format(field['id'])
            })


def create_table(context, data_dict):
    'Create table from combination of fields and first row of data.'
    check_fields(context, data_dict.get('fields'))

    create_string = 'create table "{0}" ('.format(data_dict['resource_id'])

    # add datastore fields: _id and _full_text
    create_string += '_id serial primary key, '
    create_string += '_full_text tsvector, '

    # add fields
    for field in data_dict.get('fields'):
        create_string += '"{0}" {1}, '.format(field['id'], field['type'])

    # check first row of data for additional fields
    field_ids = [field['id'] for field in data_dict.get('fields', [])]
    records = data_dict.get('records')
    if records:
        extra_field_ids = records[0].keys()
        for field_id in extra_field_ids:
            if not field_id in field_ids:
                field_type = _guess_type(records[0][field_id])
                create_string += '"{0}" {1}, '.format(field_id, field_type)

    # remove last 2 characters (a comma and a space)
    # and close the create table statement
    create_string = create_string[0:len(create_string) - 2]
    create_string += ');'

    context['connection'].execute(create_string)


def alter_table(context, data_dict):
    '''alter table from combination of fields and first row of data'''
    check_fields(context, data_dict.get('fields'))


def insert_data(context, data_dict):
    '''insert all data from records'''
    if not data_dict.get('records'):
        return

    fields = _get_fields(context, data_dict)

    for record in data_dict['records']:
        # check that number of record values is correct
        # TODO: is this necessary?
        if not len(record.keys()) == len(fields):
            error_msg = 'Field count ({0}) does not match table ({1})'.format(
                len(record.keys()), len(fields)
            )
            raise p.toolkit.ValidationError({
                'records': error_msg
            })

        sql_columns = ", ".join(['"%s"' % f['name'] for f in fields])
        sql_values = []

        for field in fields:
            if not field['name'] in record:
                raise p.toolkit.ValidationError({
                    'records': 'Field {0} not found'.format(field['name'])
                })

            if field['type'] == 'text':
                sql_values.append("'{0}'".format(record[field['name']]))
            else:
                sql_values.append('{0}'.format(record[field['name']]))

        sql_values = ", ".join(['%s' % v for v in sql_values])

        sql_string = 'insert into "{0}" ({1}) values ({2});'.format(
            data_dict['resource_id'],
            sql_columns,
            sql_values
        )

        context['connection'].execute(sql_string)


def create(context, data_dict):
    '''
    The first row will be used to guess types not in the fields and the
    guessed types will be added to the headers permanently.
    Consecutive rows have to conform to the field definitions.

    rows can be empty so that you can just set the fields.

    fields are optional but needed if you want to do type hinting or
    add extra information for certain columns or to explicitly
    define ordering.

    eg [{"id": "dob", "label": ""Date of Birth",
         "type": "timestamp" ,"concept": "day"},
        {"name": "some_stuff": ..].

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
