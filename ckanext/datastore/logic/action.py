import logging
import pylons
import ckan.logic as logic
import ckan.plugins as p
import ckanext.datastore.db as db
import sqlalchemy

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust


def datastore_create(context, data_dict):
    '''Adds a new table to the datastore.

    :param resource_id: resource id that the data is going to be stored under.
    :type resource_id: string
    :param aliases: names for read only aliases to the resource.
    :type aliases: list or comma separated string
    :param fields: fields/columns and their extra metadata.
    :type fields: list of dictionaries
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ['a', b']}]
    :type records: list of dictionaries
    :param primary_key: fields that represent a unique key
    :type primary_key: list or comma separated string
    :param indexes: indexes on table
    :type indexes: list or comma separated string

    :returns: the newly created data object.
    :rtype: dictionary

    '''
    model = _get_or_bust(context, 'model')
    id = _get_or_bust(data_dict, 'resource_id')

    if not model.Resource.get(id):
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            'Resource "{0}" was not found.'.format(id)
        ))

    p.toolkit.check_access('datastore_create', context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore.write_url']

    # validate aliases
    aliases = db._get_list(data_dict.get('aliases', []))
    for alias in aliases:
        if not db._is_valid_table_name(alias):
            raise p.toolkit.ValidationError({
                'alias': ['{0} is not a valid alias name'.format(alias)]
            })

    result = db.create(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result


def datastore_upsert(context, data_dict):
    '''Updates or inserts into a table in the datastore

    :param resource_id: resource id that the data is going to be stored under.
    :type resource_id: string
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ['a', b']}]
    :type records: list of dictionaries
    :param method: the method to use to put the data into the datastore
                    possible options: upsert (default), insert, update
        :param upsert: update if record with same key already exists,
                        otherwise insert
        :param insert: insert only, faster because checks are omitted
        :param update: update only, exception if key does not exist
    :type method: string

    :returns: the newly created data object.
    :rtype: dictionary

    '''
    res_id = _get_or_bust(data_dict, 'resource_id')

    data_dict['connection_url'] = pylons.config['ckan.datastore.read_url']

    resources_sql = sqlalchemy.text(u'''SELECT 1 FROM "_table_metadata"
                                        WHERE name = :id AND alias_of IS NULL''')
    results = db._get_engine(None, data_dict).execute(resources_sql, id=res_id)
    res_exists = results.rowcount > 0

    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            'Resource "{0}" was not found.'.format(res_id)
        ))

    p.toolkit.check_access('datastore_upsert', context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore.write_url']

    result = db.upsert(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result


def datastore_delete(context, data_dict):
    '''Deletes a table from the datastore.

    :param resource_id: resource id that the data will be deleted from.
    :type resource_id: string
    :param filter: filter to do deleting on over (eg {'name': 'fred'}).
                   If missing delete whole table and all dependent views.

    :returns: original filters sent.
    :rtype: dictionary

    '''
    res_id = _get_or_bust(data_dict, 'resource_id')

    data_dict['connection_url'] = pylons.config['ckan.datastore.read_url']

    resources_sql = sqlalchemy.text(u'''SELECT 1 FROM "_table_metadata"
                                        WHERE name = :id AND alias_of IS NULL''')
    results = db._get_engine(None, data_dict).execute(resources_sql, id=res_id)
    res_exists = results.rowcount > 0

    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            'Resource "{0}" was not found.'.format(res_id)
        ))

    p.toolkit.check_access('datastore_delete', context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore.write_url']

    result = db.delete(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result


@logic.side_effect_free
def datastore_search(context, data_dict):
    '''Search a datastore table.

    :param resource_id: id or alias of the data that is going to be selected.
    :type resource_id: string
    :param filters: matching conditions to select.
    :type filters: dictionary
    :param q: full text query
    :type q: string
    :param plain: treat as plain text query (default: true)
    :type plain: bool
    :param language: language of the full text query (default: english)
    :type language: string
    :param limit: maximum number of rows to return (default: 100)
    :type limit: int
    :param offset: offset the number of rows
    :type offset: int
    :param fields: fields to return
                   (default: all fields in original order)
    :type fields: list or comma separated string
    :param sort: comma separated field names with ordering
                 eg: "fieldname1, fieldname2 desc"
    :type sort: string

    :returns: a dictionary containing the search parameters and the
              search results.
              keys: fields: same as datastore_create accepts
                    offset: query offset value
                    limit: query limit value
                    filters: query filters
                    total: number of total matching records
                    records: list of matching results
    :rtype: dictionary

    '''
    res_id = _get_or_bust(data_dict, 'resource_id')

    data_dict['connection_url'] = pylons.config['ckan.datastore.read_url']

    resources_sql = sqlalchemy.text(u'SELECT 1 FROM "_table_metadata" WHERE name = :id')
    results = db._get_engine(None, data_dict).execute(resources_sql, id=res_id)
    res_exists = results.rowcount > 0

    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            'Resource "{0}" was not found.'.format(res_id)
        ))

    p.toolkit.check_access('datastore_search', context, data_dict)

    result = db.search(context, data_dict)
    result.pop('id', None)
    result.pop('connection_url')
    return result


@logic.side_effect_free
def datastore_search_sql(context, data_dict):
    '''Execute SQL-Queries on the datastore.

    :param sql: a single sql select statement
    :type sql: string

    :returns: a dictionary containing the search results.
              keys: fields: columns for results
                    records: results from the query
    :rtype: dictionary

    '''
    sql = _get_or_bust(data_dict, 'sql')

    if not db._is_single_statement(sql):
        raise p.toolkit.ValidationError({
            'query': ['Query is not a single statement or contains semicolons.'],
            'hint': [('If you want to use semicolons, use character encoding'
                '(; equals chr(59)) and string concatenation (||). ')]
        })

    p.toolkit.check_access('datastore_search', context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore.read_url']

    result = db.search_sql(context, data_dict)
    result.pop('id', None)
    result.pop('connection_url')
    return result
