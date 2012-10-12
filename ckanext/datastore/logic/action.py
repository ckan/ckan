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

    The datastore_create action allows a user to post JSON data to be
    stored against a resource. This endpoint also supports altering tables,
    aliases and indexes and bulk insertion.

    See :ref:`fields` and :ref:`records` for details on how to lay out records.

    :param resource_id: resource id that the data is going to be stored against.
    :type resource_id: string
    :param aliases: names for read only aliases of the resource.
    :type aliases: list or comma separated string
    :param fields: fields/columns and their extra metadata.
    :type fields: list of dictionaries
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ["a", "b"]}]
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

    The datastore_upsert API action allows a user to add or edit records to
    an existing dataStore resource. In order for the *upsert* and *update*
    methods to work, a unique key has to be defined via the datastore_create
    action. The available methods are:

    *upsert*
        Update if record with same key already exists, otherwise insert.
        Requires unique key.
    *insert*
        Insert only. This method is faster that upsert, but will fail if any
        inserted record matches an existing one. Does *not* require a unique
        key.
    *update*
        Update only. An exception will occur if the key that should be updated
        does not exist. Requires unique key.


    :param resource_id: resource id that the data is going to be stored under.
    :type resource_id: string
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ["a","b"]}]
    :type records: list of dictionaries
    :param method: the method to use to put the data into the datastore.
                   Possible options are: upsert (default), insert, update
    :type method: string

    :returns: the newly created data object.
    :rtype: dictionary

    '''
    res_id = _get_or_bust(data_dict, 'resource_id')

    data_dict['connection_url'] = pylons.config['ckan.datastore.write_url']

    resources_sql = sqlalchemy.text(u'''SELECT 1 FROM "_table_metadata"
                                        WHERE name = :id AND alias_of IS NULL''')
    results = db._get_engine(None, data_dict).execute(resources_sql, id=res_id)
    res_exists = results.rowcount > 0

    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            'Resource "{0}" was not found.'.format(res_id)
        ))

    p.toolkit.check_access('datastore_upsert', context, data_dict)

    result = db.upsert(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result


def datastore_delete(context, data_dict):
    '''Deletes a table or a set of records from the datastore.

    :param resource_id: resource id that the data will be deleted from.
    :type resource_id: string
    :param filters: filters to apply before deleting (eg {"name": "fred"}).
                   If missing delete whole table and all dependent views.
    :type filters: dictionary

    :returns: original filters sent.
    :rtype: dictionary

    '''
    res_id = _get_or_bust(data_dict, 'resource_id')

    data_dict['connection_url'] = pylons.config['ckan.datastore.write_url']

    resources_sql = sqlalchemy.text(u'''SELECT 1 FROM "_table_metadata"
                                        WHERE name = :id AND alias_of IS NULL''')
    results = db._get_engine(None, data_dict).execute(resources_sql, id=res_id)
    res_exists = results.rowcount > 0

    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            'Resource "{0}" was not found.'.format(res_id)
        ))

    p.toolkit.check_access('datastore_delete', context, data_dict)

    result = db.delete(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result


@logic.side_effect_free
def datastore_search(context, data_dict):
    '''Search a datastore table.

    The datastore_search action allows a user to search data in a resource.

    :param resource_id: id or alias of the resource to be searched against.
    :type resource_id: string
    :param filters: matching conditions to select, e.g {"key1": "a", "key2": "b"}
    :type filters: dictionary
    :param q: full text query
    :type q: string
    :param plain: treat as plain text query (default: true)
    :type plain: bool
    :param language: language of the full text query (default: english)
    :type language: string
    :param limit: maximum number of rows to return (default: 100)
    :type limit: int
    :param offset: offset this number of rows
    :type offset: int
    :param fields: fields to return (default: all fields in original order)
    :type fields: list or comma separated string
    :param sort: comma separated field names with ordering
                 e.g.: "fieldname1, fieldname2 desc"
    :type sort: string

    **Results:**

    The result of this action is a dict with the following keys:

    :rtype: A dictionary with the following keys
    :param fields: fields/columns and their extra metadata
    :type fields: list of dictionaries
    :param offset: query offset value
    :type offset: int
    :param limit: query limit value
    :type limit: int
    :param filters: query filters
    :type filters: list of dictionaries
    :param total: number of total matching records
    :type total: int
    :param records: list of matching results
    :type records: list of dictionaries

    '''
    res_id = _get_or_bust(data_dict, 'resource_id')

    data_dict['connection_url'] = pylons.config.get('ckan.datastore.read_url',
            pylons.config['ckan.datastore.write_url'])

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
    '''Execute SQL queries on the datastore.

    The datastore_search_sql action allows a user to search data in a resource
    or connect multiple resources with join expressions. The underlying SQL
    engine is the
    `PostgreSQL engine <http://www.postgresql.org/docs/9.1/interactive/sql/.html>`_

    .. note:: This action is only available when using PostgreSQL 9.X and using a read-only user on the database.
        It is not available in :ref:`legacy mode<legacy_mode>`.

    :param sql: a single sql select statement
    :type sql: string

    **Results:**

    The result of this action is a dict with the following keys:

    :rtype: A dictionary with the following keys
    :param fields: fields/columns and their extra metadata
    :type fields: list of dictionaries
    :param records: list of matching results
    :type records: list of dictionaries

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
