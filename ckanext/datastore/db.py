import sqlalchemy

_pg_types = {}
_type_names = set()
_engines = {}


class InvalidType(Exception):
    pass


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


def check_fields(context, fields):
    'Check if field types are valid.'
    _cache_types(context)
    for field in fields:
        if not field['type'] in _type_names:
            raise InvalidType('%s is not a valid type' % field['type'])


def create_table(context, data_dict):
    '''create table from combination of fields and first row of data'''
    check_fields(context, data_dict.get('fields'))
    pass


def alter_table(context, data_dict):
    '''alter table from combination of fields and first row of data'''
    check_fields(context, data_dict.get('fields'))
    pass


def insert_data(context, data_dict):
    '''insert all data from records'''
    pass


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
    except:
        trans.rollback()
        raise
    finally:
        context['connection'].close()
