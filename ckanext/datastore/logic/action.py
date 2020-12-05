# encoding: utf-8

import logging
import json

import sqlalchemy
import six
from six import text_type

import ckan.lib.search as search
import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.plugins as p
from ckan.common import config
import ckanext.datastore.logic.schema as dsschema
import ckanext.datastore.helpers as datastore_helpers
from ckanext.datastore.backend import (
    DatastoreBackend, InvalidDataError
)
from ckanext.datastore.backend.postgres import identifier

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust
_validate = ckan.lib.navl.dictization_functions.validate

WHITELISTED_RESOURCES = ['_table_metadata']


def datastore_create(context, data_dict):
    '''Adds a new table to the DataStore.

    The datastore_create action allows you to post JSON data to be
    stored against a resource. This endpoint also supports altering tables,
    aliases and indexes and bulk insertion. This endpoint can be called
    multiple times to initially insert more data, add fields, change the
    aliases or indexes as well as the primary keys.

    To create an empty datastore resource and a CKAN resource at the same time,
    provide ``resource`` with a valid ``package_id`` and omit the
    ``resource_id``.

    If you want to create a datastore resource from the content of a file,
    provide ``resource`` with a valid ``url``.

    See :ref:`fields` and :ref:`records` for details on how to lay out records.

    :param resource_id: resource id that the data is going to be stored
                        against.
    :type resource_id: string
    :param force: set to True to edit a read-only resource
    :type force: bool (optional, default: False)
    :param resource: resource dictionary that is passed to
        :meth:`~ckan.logic.action.create.resource_create`.
        Use instead of ``resource_id`` (optional)
    :type resource: dictionary
    :param aliases: names for read only aliases of the resource. (optional)
    :type aliases: list or comma separated string
    :param fields: fields/columns and their extra metadata. (optional)
    :type fields: list of dictionaries
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ["a", "b"]}]
                    (optional)
    :type records: list of dictionaries
    :param primary_key: fields that represent a unique key (optional)
    :type primary_key: list or comma separated string
    :param indexes: indexes on table (optional)
    :type indexes: list or comma separated string
    :param triggers: trigger functions to apply to this table on update/insert.
        functions may be created with
        :meth:`~ckanext.datastore.logic.action.datastore_function_create`.
        eg: [
        {"function": "trigger_clean_reference"},
        {"function": "trigger_check_codes"}]
    :type triggers: list of dictionaries
    :param calculate_record_count: updates the stored count of records, used to
        optimize datastore_search in combination with the
        `total_estimation_threshold` parameter. If doing a series of requests
        to change a resource, you only need to set this to True on the last
        request.
    :type calculate_record_count: bool (optional, default: False)

    Please note that setting the ``aliases``, ``indexes`` or ``primary_key``
    replaces the existing aliases or constraints. Setting ``records`` appends
    the provided records to the resource.

    **Results:**

    :returns: The newly created data object, excluding ``records`` passed.
    :rtype: dictionary

    See :ref:`fields` and :ref:`records` for details on how to lay out records.

    '''
    backend = DatastoreBackend.get_active_backend()
    schema = context.get('schema', dsschema.datastore_create_schema())
    records = data_dict.pop('records', None)
    resource = data_dict.pop('resource', None)
    data_dict, errors = _validate(data_dict, schema, context)
    resource_dict = None
    if records:
        data_dict['records'] = records
    if resource:
        data_dict['resource'] = resource
    if errors:
        raise p.toolkit.ValidationError(errors)

    p.toolkit.check_access('datastore_create', context, data_dict)

    if 'resource' in data_dict and 'resource_id' in data_dict:
        raise p.toolkit.ValidationError({
            'resource': ['resource cannot be used with resource_id']
        })

    if 'resource' not in data_dict and 'resource_id' not in data_dict:
        raise p.toolkit.ValidationError({
            'resource_id': ['resource_id or resource required']
        })

    if 'resource' in data_dict:
        has_url = 'url' in data_dict['resource']
        # A datastore only resource does not have a url in the db
        data_dict['resource'].setdefault('url', '_datastore_only_resource')
        resource_dict = p.toolkit.get_action('resource_create')(
            context, data_dict['resource'])
        data_dict['resource_id'] = resource_dict['id']

        # create resource from file
        if has_url:
            if not p.plugin_loaded('datapusher'):
                raise p.toolkit.ValidationError({'resource': [
                    'The datapusher has to be enabled.']})
            p.toolkit.get_action('datapusher_submit')(context, {
                'resource_id': resource_dict['id'],
                'set_url_type': True
            })
            # since we'll overwrite the datastore resource anyway, we
            # don't need to create it here
            return

        # create empty resource
        else:
            # no need to set the full url because it will be set in before_show
            resource_dict['url_type'] = 'datastore'
            p.toolkit.get_action('resource_update')(context, resource_dict)
    else:
        if not data_dict.pop('force', False):
            resource_id = data_dict['resource_id']
            _check_read_only(context, resource_id)

    # validate aliases
    aliases = datastore_helpers.get_list(data_dict.get('aliases', []))
    for alias in aliases:
        if not datastore_helpers.is_valid_table_name(alias):
            raise p.toolkit.ValidationError({
                'alias': [u'"{0}" is not a valid alias name'.format(alias)]
            })

    try:
        result = backend.create(context, data_dict)
    except InvalidDataError as err:
        raise p.toolkit.ValidationError(text_type(err))

    if data_dict.get('calculate_record_count', False):
        backend.calculate_record_count(data_dict['resource_id'])

    # Set the datastore_active flag on the resource if necessary
    model = _get_or_bust(context, 'model')
    resobj = model.Resource.get(data_dict['resource_id'])
    if resobj.extras.get('datastore_active') is not True:
        log.debug(
            'Setting datastore_active=True on resource {0}'.format(resobj.id)
        )
        set_datastore_active_flag(model, data_dict, True)

    result.pop('id', None)
    result.pop('connection_url', None)
    result.pop('records', None)
    return result


def datastore_run_triggers(context, data_dict):
    ''' update each record with trigger

    The datastore_run_triggers API action allows you to re-apply existing
    triggers to an existing DataStore resource.

    :param resource_id: resource id that the data is going to be stored under.
    :type resource_id: string

    **Results:**

    :returns: The rowcount in the table.
    :rtype: int

    '''
    res_id = data_dict['resource_id']
    p.toolkit.check_access('datastore_run_triggers', context, data_dict)
    backend = DatastoreBackend.get_active_backend()
    connection = backend._get_write_engine().connect()

    sql = sqlalchemy.text(u'''update {0} set _id=_id '''.format(
                          identifier(res_id)))
    try:
        results = connection.execute(sql)
    except sqlalchemy.exc.DatabaseError as err:
        message = six.ensure_text(err.args[0].split('\n')[0])
        raise p.toolkit.ValidationError({
                u'records': [message.split(u') ', 1)[-1]]})
    return results.rowcount


def datastore_upsert(context, data_dict):
    '''Updates or inserts into a table in the DataStore

    The datastore_upsert API action allows you to add or edit records to
    an existing DataStore resource. In order for the *upsert* and *update*
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
    :param force: set to True to edit a read-only resource
    :type force: bool (optional, default: False)
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ["a","b"]}]
                    (optional)
    :type records: list of dictionaries
    :param method: the method to use to put the data into the datastore.
                   Possible options are: upsert, insert, update
                   (optional, default: upsert)
    :type method: string
    :param calculate_record_count: updates the stored count of records, used to
        optimize datastore_search in combination with the
        `total_estimation_threshold` parameter. If doing a series of requests
        to change a resource, you only need to set this to True on the last
        request.
    :type calculate_record_count: bool (optional, default: False)
    :param dry_run: set to True to abort transaction instead of committing,
                    e.g. to check for validation or type errors.
    :type dry_run: bool (optional, default: False)

    **Results:**

    :returns: The modified data object.
    :rtype: dictionary

    '''
    backend = DatastoreBackend.get_active_backend()
    schema = context.get('schema', dsschema.datastore_upsert_schema())
    records = data_dict.pop('records', None)
    data_dict, errors = _validate(data_dict, schema, context)
    if records:
        data_dict['records'] = records
    if errors:
        raise p.toolkit.ValidationError(errors)

    p.toolkit.check_access('datastore_upsert', context, data_dict)

    resource_id = data_dict['resource_id']

    if not data_dict.pop('force', False):
        _check_read_only(context, resource_id)

    res_exists = backend.resource_exists(resource_id)
    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            u'Resource "{0}" was not found.'.format(resource_id)
        ))

    result = backend.upsert(context, data_dict)
    result.pop('id', None)
    result.pop('connection_url', None)

    if data_dict.get('calculate_record_count', False):
        backend.calculate_record_count(data_dict['resource_id'])

    return result


def datastore_info(context, data_dict):
    '''
    Returns information about the data imported, such as column names
    and types.

    :rtype: A dictionary describing the columns and their types.
    :param id: Id of the resource we want info about
    :type id: A UUID
    '''
    backend = DatastoreBackend.get_active_backend()

    p.toolkit.check_access('datastore_info', context, data_dict)

    resource_id = _get_or_bust(data_dict, 'id')
    p.toolkit.get_action('resource_show')(context, {'id': resource_id})

    res_exists = backend.resource_exists(resource_id)
    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            u'Resource "{0}" was not found.'.format(resource_id)
        ))

    info = backend.resource_fields(resource_id)

    return info


def datastore_delete(context, data_dict):
    '''Deletes a table or a set of records from the DataStore.

    :param resource_id: resource id that the data will be deleted from.
                        (optional)
    :type resource_id: string
    :param force: set to True to edit a read-only resource
    :type force: bool (optional, default: False)
    :param filters: filters to apply before deleting (eg {"name": "fred"}).
                   If missing delete whole table and all dependent views.
                   (optional)
    :type filters: dictionary
    :param calculate_record_count: updates the stored count of records, used to
        optimize datastore_search in combination with the
        `total_estimation_threshold` parameter. If doing a series of requests
        to change a resource, you only need to set this to True on the last
        request.
    :type calculate_record_count: bool (optional, default: False)

    **Results:**

    :returns: Original filters sent.
    :rtype: dictionary

    '''
    schema = context.get('schema', dsschema.datastore_delete_schema())
    backend = DatastoreBackend.get_active_backend()

    # Remove any applied filters before running validation.
    filters = data_dict.pop('filters', None)
    data_dict, errors = _validate(data_dict, schema, context)

    if filters is not None:
        if not isinstance(filters, dict):
            raise p.toolkit.ValidationError({
                'filters': [
                    'filters must be either a dict or null.'
                ]
            })
        data_dict['filters'] = filters

    if errors:
        raise p.toolkit.ValidationError(errors)

    p.toolkit.check_access('datastore_delete', context, data_dict)

    if not data_dict.pop('force', False):
        resource_id = data_dict['resource_id']
        _check_read_only(context, resource_id)

    res_id = data_dict['resource_id']

    res_exists = backend.resource_exists(res_id)

    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            u'Resource "{0}" was not found.'.format(res_id)
        ))

    result = backend.delete(context, data_dict)

    if data_dict.get('calculate_record_count', False):
        backend.calculate_record_count(data_dict['resource_id'])

    # Set the datastore_active flag on the resource if necessary
    model = _get_or_bust(context, 'model')
    resource = model.Resource.get(data_dict['resource_id'])

    if (not data_dict.get('filters') and
            resource is not None and
            resource.extras.get('datastore_active') is True):
        log.debug(
            'Setting datastore_active=False on resource {0}'.format(
                resource.id)
        )
        set_datastore_active_flag(model, data_dict, False)

    result.pop('id', None)
    result.pop('connection_url', None)
    return result


@logic.side_effect_free
def datastore_search(context, data_dict):
    '''Search a DataStore resource.

    The datastore_search action allows you to search data in a resource. By
    default 100 rows are returned - see the `limit` parameter for more info.

    A DataStore resource that belongs to a private CKAN resource can only be
    read by you if you have access to the CKAN resource and send the
    appropriate authorization.

    :param resource_id: id or alias of the resource to be searched against
    :type resource_id: string
    :param filters: matching conditions to select, e.g
                    {"key1": "a", "key2": "b"} (optional)
    :type filters: dictionary
    :param q: full text query. If it's a string, it'll search on all fields on
              each row. If it's a dictionary as {"key1": "a", "key2": "b"},
              it'll search on each specific field (optional)
    :type q: string or dictionary
    :param distinct: return only distinct rows (optional, default: false)
    :type distinct: bool
    :param plain: treat as plain text query (optional, default: true)
    :type plain: bool
    :param language: language of the full text query
                     (optional, default: english)
    :type language: string
    :param limit: maximum number of rows to return
        (optional, default: ``100``, unless set in the site's configuration
        ``ckan.datastore.search.rows_default``, upper limit: ``32000`` unless
        set in site's configuration ``ckan.datastore.search.rows_max``)
    :type limit: int
    :param offset: offset this number of rows (optional)
    :type offset: int
    :param fields: fields to return
                   (optional, default: all fields in original order)
    :type fields: list or comma separated string
    :param sort: comma separated field names with ordering
                 e.g.: "fieldname1, fieldname2 desc"
    :type sort: string
    :param include_total: True to return total matching record count
                          (optional, default: true)
    :type include_total: bool
    :param total_estimation_threshold: If "include_total" is True and
        "total_estimation_threshold" is not None and the estimated total
        (matching record count) is above the "total_estimation_threshold" then
        this datastore_search will return an *estimate* of the total, rather
        than a precise one. This is often good enough, and saves
        computationally expensive row counting for larger results (e.g. >100000
        rows). The estimated total comes from the PostgreSQL table statistics,
        generated when Express Loader or DataPusher finishes a load, or by
        autovacuum. NB Currently estimation can't be done if the user specifies
        'filters' or 'distinct' options. (optional, default: None)
    :type total_estimation_threshold: int or None
    :param records_format: the format for the records return value:
        'objects' (default) list of {fieldname1: value1, ...} dicts,
        'lists' list of [value1, value2, ...] lists,
        'csv' string containing comma-separated values with no header,
        'tsv' string containing tab-separated values with no header
    :type records_format: controlled list


    Setting the ``plain`` flag to false enables the entire PostgreSQL
    `full text search query language`_.

    A listing of all available resources can be found at the
    alias ``_table_metadata``.

    .. _full text search query language: http://www.postgresql.org/docs/9.1/static/datatype-textsearch.html#DATATYPE-TSQUERY

    If you need to download the full resource, read :ref:`dump`.

    **Results:**

    The result of this action is a dictionary with the following keys:

    :rtype: A dictionary with the following keys
    :param fields: fields/columns and their extra metadata
    :type fields: list of dictionaries
    :param offset: query offset value
    :type offset: int
    :param limit: queried limit value (if the requested ``limit`` was above the
        ``ckan.datastore.search.rows_max`` value then this response ``limit``
        will be set to the value of ``ckan.datastore.search.rows_max``)
    :type limit: int
    :param filters: query filters
    :type filters: list of dictionaries
    :param total: number of total matching records
    :type total: int
    :param total_was_estimated: whether or not the total was estimated
    :type total_was_estimated: bool
    :param records: list of matching results
    :type records: depends on records_format value passed

    '''
    backend = DatastoreBackend.get_active_backend()
    schema = context.get('schema', dsschema.datastore_search_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    res_id = data_dict['resource_id']

    if data_dict['resource_id'] not in WHITELISTED_RESOURCES:
        res_exists, real_id = backend.resource_id_from_alias(res_id)
        # Resource only has to exist in the datastore (because it could be an
        # alias)

        if not res_exists:
            raise p.toolkit.ObjectNotFound(p.toolkit._(
                'Resource "{0}" was not found.'.format(res_id)
            ))

        # Replace potential alias with real id to simplify access checks
        if real_id:
            data_dict['resource_id'] = real_id

        p.toolkit.check_access('datastore_search', context, data_dict)

    result = backend.search(context, data_dict)
    result.pop('id', None)
    result.pop('connection_url', None)
    return result


@logic.side_effect_free
def datastore_search_sql(context, data_dict):
    '''Execute SQL queries on the DataStore.

    The datastore_search_sql action allows a user to search data in a resource
    or connect multiple resources with join expressions. The underlying SQL
    engine is the
    `PostgreSQL engine <http://www.postgresql.org/docs/9.1/interactive/>`_.
    There is an enforced timeout on SQL queries to avoid an unintended DOS.
    The number of results returned is limited to 32000, unless set in the
    site's configuration ``ckan.datastore.search.rows_max``
    Queries are only allowed if you have access to the all the CKAN resources
    in the query and send the appropriate authorization.

    .. note:: This action is not available when
        :ref:`ckan.datastore.sqlsearch.enabled` is set to false

    .. note:: When source data columns (i.e. CSV) heading names are provided
        in all UPPERCASE you need to double quote them in the SQL select
        statement to avoid returning null results.

    :param sql: a single SQL select statement
    :type sql: string

    **Results:**

    The result of this action is a dictionary with the following keys:

    :rtype: A dictionary with the following keys
    :param fields: fields/columns and their extra metadata
    :type fields: list of dictionaries
    :param records: list of matching results
    :type records: list of dictionaries
    :param records_truncated: indicates whether the number of records returned
        was limited by the internal limit, which is 32000 records (or other
        value set in the site's configuration
        ``ckan.datastore.search.rows_max``). If records are truncated by this,
        this key has value True, otherwise the key is not returned at all.
    :type records_truncated: bool

    '''
    backend = DatastoreBackend.get_active_backend()

    def check_access(table_names):
        '''
        Raise NotAuthorized if current user is not allowed to access
        any of the tables passed

        :type table_names: list strings
        '''
        p.toolkit.check_access(
            'datastore_search_sql',
            dict(context, table_names=table_names),
            data_dict)

    result = backend.search_sql(
        dict(context, check_access=check_access),
        data_dict)
    result.pop('id', None)
    result.pop('connection_url', None)
    return result


def set_datastore_active_flag(model, data_dict, flag):
    '''
    Set appropriate datastore_active flag on CKAN resource.

    Called after creation or deletion of DataStore table.
    '''
    # We're modifying the resource extra directly here to avoid a
    # race condition, see issue #3245 for details and plan for a
    # better fix
    update_dict = {'datastore_active': flag}

    # get extras(for entity update) and package_id(for search index update)
    res_query = model.Session.query(
        model.resource_table.c.extras,
        model.resource_table.c.package_id
    ).filter(
        model.Resource.id == data_dict['resource_id']
    )
    extras, package_id = res_query.one()

    # update extras in database for record
    extras.update(update_dict)
    res_query.update({'extras': extras}, synchronize_session=False)

    model.Session.commit()

    # get package with  updated resource from solr
    # find changed resource, patch it and reindex package
    psi = search.PackageSearchIndex()
    solr_query = search.PackageSearchQuery()
    q = {
        'q': 'id:"{0}"'.format(package_id),
        'fl': 'data_dict',
        'wt': 'json',
        'fq': 'site_id:"%s"' % config.get('ckan.site_id'),
        'rows': 1
    }
    for record in solr_query.run(q)['results']:
        solr_data_dict = json.loads(record['data_dict'])
        for resource in solr_data_dict['resources']:
            if resource['id'] == data_dict['resource_id']:
                resource.update(update_dict)
                psi.index_package(solr_data_dict)
                break


def _resource_exists(context, data_dict):
    ''' Returns true if the resource exists in CKAN and in the datastore '''
    model = _get_or_bust(context, 'model')
    res_id = _get_or_bust(data_dict, 'resource_id')
    if not model.Resource.get(res_id):
        return False

    backend = DatastoreBackend.get_active_backend()

    return backend.resource_exists(res_id)


def _check_read_only(context, resource_id):
    ''' Raises exception if the resource is read-only.
    Make sure the resource id is in resource_id
    '''
    res = p.toolkit.get_action('resource_show')(
        context, {'id': resource_id})
    if res.get('url_type') != 'datastore':
        raise p.toolkit.ValidationError({
            'read-only': ['Cannot edit read-only resource. Either pass'
                          '"force=True" or change url_type to "datastore"']
        })


@logic.validate(dsschema.datastore_function_create_schema)
def datastore_function_create(context, data_dict):
    u'''
    Create a trigger function for use with datastore_create

    :param name: function name
    :type name: string
    :param or_replace: True to replace if function already exists
        (default: False)
    :type or_replace: bool
    :param rettype: set to 'trigger'
        (only trigger functions may be created at this time)
    :type rettype: string
    :param definition: PL/pgSQL function body for trigger function
    :type definition: string
    '''
    p.toolkit.check_access('datastore_function_create', context, data_dict)
    backend = DatastoreBackend.get_active_backend()
    backend.create_function(
        name=data_dict['name'],
        arguments=data_dict.get('arguments', []),
        rettype=data_dict['rettype'],
        definition=data_dict['definition'],
        or_replace=data_dict['or_replace'])


@logic.validate(dsschema.datastore_function_delete_schema)
def datastore_function_delete(context, data_dict):
    u'''
    Delete a trigger function

    :param name: function name
    :type name: string
    '''
    p.toolkit.check_access('datastore_function_delete', context, data_dict)
    backend = DatastoreBackend.get_active_backend()
    backend.drop_function(data_dict['name'], data_dict['if_exists'])
