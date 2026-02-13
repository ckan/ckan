# encoding: utf-8
from __future__ import annotations

from ckan.types import Context
import logging
from typing import Any
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

import sqlalchemy
import sqlalchemy.exc

import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckanext.datastore.logic.schema as dsschema
import ckanext.datastore.helpers as datastore_helpers
from ckanext.datastore.backend import DatastoreBackend
from ckanext.datastore.backend.postgres import identifier
from ckanext.datastore import interfaces

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust
_validate = ckan.lib.navl.dictization_functions.validate

WHITELISTED_RESOURCES = ['_table_metadata']

RESOURCE_LAST_MODIFIED_SETTLE_TIME = timedelta(seconds=15)


def datastore_create(context: Context, data_dict: dict[str, Any]):
    '''Adds a new table to the DataStore.

    The datastore_create action allows you to post JSON data to be
    stored against a resource. This endpoint also supports altering tables,
    aliases and indexes and bulk insertion. This endpoint can be called
    multiple times to initially insert more data, add/remove fields, change the
    aliases or indexes as well as the primary keys.

    To create a writable table and a CKAN resource at the same time,
    provide ``resource`` with a valid ``package_id`` and omit the
    ``resource_id``.

    See :ref:`fields` and :ref:`records` for details on how to lay out records.

    :param resource_id: resource id that the data is going to be stored
                        against.
    :type resource_id: string
    :param force: set to True to edit a read-only table
    :type force: bool (optional, default: False)
    :param resource: resource dictionary that is passed to
        :meth:`~ckan.logic.action.create.resource_create`.
        Use instead of ``resource_id`` (optional)
    :type resource: dictionary
    :param aliases: names for read only aliases of the resource. (optional)
    :type aliases: list or comma separated string
    :param fields: fields/columns and their extra metadata. (optional)
    :type fields: list of dictionaries
    :param delete_fields: set to True to remove existing fields not passed
    :type delete_fields: bool (optional, default: False)
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ["a", "b"]}]
                    (optional)
    :type records: list of dictionaries
    :param include_records: return the full values of inserted records
                            (optional, default: False)
    :type include_records: bool
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
    :param calculate_record_count: False: don't update the count, True: update
        the count immediately, "background": schedule a background job to update
        the record count. The stored count of records is used to optimize
        datastore_search total count response. If doing a series of requests to
        change a resource, set this to False for all but the last request.
        (optional, default: "background")
    :type calculate_record_count: True, False or "background"

    Please note that setting the ``aliases``, ``indexes`` or ``primary_key``
    replaces the existing aliases or constraints. Setting ``records`` appends
    the provided records to the resource. Setting ``fields`` without including
    all existing fields will remove the others and the data they contain
    when delete_fields=True.

    For writable tables the resource ``last_modified`` value will be updated
    by a scheduled background job. See :ref:`background jobs` for more
    information.

    **Results:**

    :returns: The newly created data object, excluding ``records`` passed.
    :rtype: dictionary

    See :ref:`fields` and :ref:`records` for details on how to lay out records.

    '''
    backend = DatastoreBackend.get_active_backend()
    schema = context.get('schema', dsschema.datastore_create_schema())
    records = data_dict.pop('records', None)
    resource = data_dict.pop('resource', None)
    for plugin in p.PluginImplementations(interfaces.IDataDictionaryForm):
        schema = plugin.update_datastore_create_schema(schema)
    with _create_validate_context(context, data_dict) as validate_context:
        plugin_data = validate_context['plugin_data']
        data_dict, errors = _validate(data_dict, schema, validate_context)
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
        resource_data = dict(data_dict['resource'])
        # create resource from file
        if has_url:
            # FIXME: xloader? datapusher+?
            if not p.plugin_loaded('datapusher'):
                raise p.toolkit.ValidationError({'resource': [
                    'The datapusher has to be enabled.']})
        else:
            resource_data['last_modified'] = datetime.now(timezone.utc)
            resource_data['url_type'] = 'datastore'

        res = p.toolkit.get_action('resource_create')(
            p.toolkit.fresh_context(context), resource_data
        )
        data_dict['resource_id'] = res['id']

        if has_url:
            # FIXME: xloader? datapusher+?
            p.toolkit.get_action('datapusher_submit')(context, {
                'resource_id': res['id'],
                'set_url_type': True
            })
            # since we'll overwrite the datastore resource anyway, we
            # don't need to create it here
            return
    else:
        res = p.toolkit.get_action('resource_show')(
            p.toolkit.fresh_context(context), {'id': data_dict['resource_id']})
        if not data_dict.pop('force', False):
            _check_read_only(res)

    # validate aliases
    aliases = datastore_helpers.get_list(data_dict.get('aliases', [])) or []
    for alias in aliases:
        if not datastore_helpers.is_valid_table_name(alias):
            raise p.toolkit.ValidationError({
                'alias': [u'"{0}" is not a valid alias name'.format(alias)]
            })

    ccount = data_dict['calculate_record_count']
    ccancel = False
    if ccount:
        ccancel = _cancel_calculate_record_count(res['id'])

    try:
        result = backend.create(context, data_dict, plugin_data)
    except:
        # if we canceled an earlier count job, reschedule before failing
        if ccancel:
            _schedule_calculate_record_count(res['id'])
        raise

    if not ccount or ccount == 'background':
        backend.clear_table_stats(res['id'])
    if ccount == 'background':
        _schedule_calculate_record_count(res['id'])
    elif ccount:
        backend.calculate_record_count(res['id'])

    # Set the datastore_active flag on the resource if necessary
    resobj = model.Resource.get(data_dict['resource_id'])
    if resobj and not resobj.extras.get('datastore_active'):
        log.debug(
            'Setting datastore_active=True on resource %s', resobj.id,
        )
        patch_kwargs = {
            'id': data_dict['resource_id'], 'datastore_active': True,
        }
        if ('resource' not in data_dict and res.get('url_type')
            in p.toolkit.h.datastore_rw_resource_url_types()
        ):
            patch_kwargs['last_modified'] = datetime.now(timezone.utc)
        p.toolkit.get_action('resource_patch')(
            p.toolkit.fresh_context(context), patch_kwargs
        )
    elif 'resource' not in data_dict and res.get('url_type') in (
        p.toolkit.h.datastore_rw_resource_url_types()
    ):
        _schedule_patch_resource_last_modified(res['id'])

    result.pop('id', None)
    result.pop('connection_url', None)
    if not data_dict.pop('include_records', False):
        result.pop('records', None)
    return result


@contextmanager
def _create_validate_context(context: Context, data_dict: dict[str, Any]):
    '''
    Populate plugin_data and resource for context to validators of
    datastore_create data_dict. This is called before validation so nothing
    about data_dict can be trusted.
    '''
    backend = DatastoreBackend.get_active_backend()
    validate_context = p.toolkit.fresh_context(context)
    plugin_data: dict[int, dict[str, Any]] = {}
    validate_context['plugin_data'] = plugin_data
    resource_id = data_dict.get('resource_id')
    if not resource_id or not isinstance(resource_id, str):
        yield validate_context
        return

    resource = model.Resource.get(data_dict['resource_id'])
    if not resource:
        yield validate_context
        return
    validate_context['resource'] = resource

    fields = data_dict.get('fields')
    if not fields or not isinstance(fields, list):
        yield validate_context
        return

    try:
        current_plugin_data = backend.resource_plugin_data(resource_id)
    except NotImplementedError:
        current_plugin_data = None
    if not current_plugin_data:
        yield validate_context
        return

    for i, field in enumerate(data_dict['fields']):
        if not isinstance(field, dict):
            continue
        if field.get('id') in current_plugin_data:
            plugin_data[i] = {'_current': current_plugin_data[field['id']]}
    yield validate_context

    # clean up _current values so they aren't saved
    for pd in plugin_data.values():
        pd.pop('_current', None)


def datastore_run_triggers(context: Context, data_dict: dict[str, Any]) -> int:
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
    connection = backend._get_write_engine().connect()  # type: ignore

    sql = sqlalchemy.text(u'''update {0} set _id=_id '''.format(
                          identifier(res_id)))
    try:
        results: Any = connection.execute(sql)
    except sqlalchemy.exc.DatabaseError as err:
        message = str(err.args[0].split('\n')[0])
        raise p.toolkit.ValidationError({
                u'records': [message.split(u') ', 1)[-1]]})
    return results.rowcount


def datastore_upsert(context: Context, data_dict: dict[str, Any]):
    '''Updates or inserts into a table in the DataStore

    The datastore_upsert API action allows you to add or edit records to
    an existing DataStore resource. In order for the *upsert* and *update*
    methods to work, a unique key has to be defined via the datastore_create
    action. The available methods are:

    *upsert*
        Update if record with same key already exists, otherwise insert.
        Requires unique key or _id field.
    *insert*
        Insert only. This method is faster that upsert, but will fail if any
        inserted record matches an existing one. Does *not* require a unique
        key.
    *update*
        Update only. An exception will occur if the key that should be updated
        does not exist. Requires unique key or _id field.


    :param resource_id: resource id that the data is going to be stored under.
    :type resource_id: string
    :param force: set to True to edit a read-only table
    :type force: bool (optional, default: False)
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ["a","b"]}]
                    (optional)
    :type records: list of dictionaries
    :param include_records: return the full values of inserted records
                            (optional, default: False)
    :type include_records: bool
    :param method: the method to use to put the data into the datastore.
                   Possible options are: upsert, insert, update
                   (optional, default: upsert)
    :type method: string
    :param calculate_record_count: False: don't update the count, True: update
        the count immediately, "background": schedule a background job to update
        the record count. The stored count of records is used to optimize
        datastore_search total count response. If doing a series of requests to
        change a resource, set this to False for all but the last request.
        (optional, default: "background")
    :type calculate_record_count: True, False or "background"
    :param dry_run: set to True to abort transaction instead of committing,
                    e.g. to check for validation or type errors.
    :type dry_run: bool (optional, default: False)

    For writable tables the resource ``last_modified`` value will be updated
    by a scheduled background job. See :ref:`background jobs` for more
    information.

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

    res = p.toolkit.get_action('resource_show')(
        p.toolkit.fresh_context(context), {'id': resource_id})
    if not data_dict.pop('force', False):
        _check_read_only(res)

    res_exists = backend.resource_exists(resource_id)
    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            u'Resource "{0}" was not found.'.format(resource_id)
        ))

    ccount = data_dict['calculate_record_count']
    ccancel = False
    if ccount:
        ccancel = _cancel_calculate_record_count(resource_id)

    try:
        result = backend.upsert(context, data_dict)
    except:
        # if we canceled an earlier count job, reschedule before failing
        if ccancel:
            _schedule_calculate_record_count(resource_id)
        raise

    p.toolkit.signals.datastore_upsert.send(resource_id, records=records)

    result.pop('id', None)
    result.pop('connection_url', None)
    if not data_dict.pop('include_records', False):
        result.pop('records', None)

    if not ccount or ccount == 'background':
        backend.clear_table_stats(res['id'])
    if ccount == 'background':
        _schedule_calculate_record_count(res['id'])
    elif ccount:
        backend.calculate_record_count(res['id'])

    if res.get('url_type') in p.toolkit.h.datastore_rw_resource_url_types():
        _schedule_patch_resource_last_modified(resource_id)

    return result


@logic.side_effect_free
def datastore_info(context: Context, data_dict: dict[str, Any]
        ) -> dict[str, Any]:
    '''
    Returns detailed metadata about a resource.

    :param resource_id: id or alias of the resource we want info about.
    :type resource_id: string
    :param include_meta: return table size, index size, row count and aliases
    :type include_meta: bool (optional, default: True)
    :param include_fields_schema: return fields' index, unique, notnull status
    :type include_fields_schema: bool (optional, default: True)

    **Results:**

    :rtype: dictionary
    :returns:
        **meta**: resource metadata dictionary with the following keys:

        - aliases - aliases (views) for the resource
        - count - row count
        - db_size - size of the datastore database (bytes)
        - id - resource id (useful for dereferencing aliases)
        - idx_size - size of all indices for the resource (bytes)
        - size - size of resource (bytes)
        - table_type - BASE TABLE, VIEW, FOREIGN TABLE or MATERIALIZED VIEW

        **fields**: A list of dictionaries based on :ref:`fields`, with an
        additional nested dictionary per field called **schema**, with the
        following keys:

        - native_type - native database data type
        - index_name
        - is_index
        - notnull
        - uniquekey

    '''
    backend = DatastoreBackend.get_active_backend()
    schema = dsschema.datastore_info_schema()
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    resource_id = data_dict['resource_id']
    res_exists = backend.resource_exists(resource_id)
    if not res_exists:
        alias_exists, real_id = backend.resource_id_from_alias(resource_id)
        if not alias_exists:
            raise p.toolkit.ObjectNotFound(p.toolkit._(
                u'Resource/Alias "{0}" was not found.'.format(resource_id)
            ))
        else:
            id = real_id
    else:
        id = resource_id

    data_dict['id'] = id
    p.toolkit.check_access('datastore_info', context, data_dict)

    p.toolkit.get_action('resource_show')(context, {'id': id})

    info = backend.resource_fields(
        id, data_dict['include_meta'], data_dict['include_fields_schema'])

    try:
        plugin_data = backend.resource_plugin_data(id)
    except NotImplementedError:
        return {}

    for i, field in enumerate(info['fields']):
        for plugin in p.PluginImplementations(interfaces.IDataDictionaryForm):
            field = plugin.update_datastore_info_field(
                field, plugin_data.get(field['id'], {}))
        info['fields'][i] = field
    return info


def datastore_delete(context: Context, data_dict: dict[str, Any]):
    '''Deletes a table or a set of records from the DataStore.
    (Use :py:func:`~ckanext.datastore.logic.action.datastore_records_delete` to keep tables intact)

    :param resource_id: resource id that the data will be deleted from.
                        (optional)
    :type resource_id: string
    :param force: set to True to edit a read-only resource
    :type force: bool (optional, default: False)
    :param filters: :ref:`filters` to apply before deleting (eg {"name": "fred"}).
                   If missing delete whole table and all dependent views.
                   (optional)
    :type filters: dictionary
    :param include_deleted_records: return the full values of deleted records
                                    (optional, default: False)
    :type include_deleted_records: bool
    :param calculate_record_count: False: don't update the count, True: update
        the count immediately, "background": schedule a background job to update
        the record count. The stored count of records is used to optimize
        datastore_search total count response. If doing a series of requests to
        change a resource, set this to False for all but the last request.
        (optional, default: "background")
    :type calculate_record_count: True, False or "background"

    For writable tables the resource ``last_modified`` value will be updated
    by a scheduled background job. See :ref:`background jobs` for more
    information.

    **Results:**

    :returns: Original filters sent and list of deleted_records
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

    resource_id = data_dict['resource_id']

    res = p.toolkit.get_action('resource_show')(
        p.toolkit.fresh_context(context), {'id': resource_id})
    if not data_dict.pop('force', False):
        _check_read_only(res)

    res_exists = backend.resource_exists(resource_id)

    if not res_exists:
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            u'Resource "{0}" was not found.'.format(resource_id)
        ))

    ccount = data_dict.pop('calculate_record_count')
    ccancel = False
    if ccount:
        ccancel = _cancel_calculate_record_count(resource_id)

    try:
        result = backend.delete(context, data_dict)
    except:
        # if we canceled an earlier count job, reschedule before failing
        if ccancel:
            _schedule_calculate_record_count(resource_id)
        raise

    p.toolkit.signals.datastore_delete.send(
        resource_id, result=result, data_dict=data_dict)

    if not ccount or ccount == 'background':
        backend.clear_table_stats(resource_id)
    if ccount == 'background':
        _schedule_calculate_record_count(resource_id)
    elif ccount:
        backend.calculate_record_count(resource_id)

    # Set the datastore_active flag on the resource if necessary
    if data_dict.get('filters', None) is None and res.get('datastore_active'):
        log.debug(
            'Setting datastore_active=False on resource %s', resource_id,
        )
        patch_kwargs = {
            'id': resource_id, 'datastore_active': False,
        }
        if res.get('url_type') in p.toolkit.h.datastore_rw_resource_url_types():
            patch_kwargs['last_modified'] = datetime.now(timezone.utc)
            _cancel_patch_resource_last_modified(resource_id)
        p.toolkit.get_action('resource_patch')(
            p.toolkit.fresh_context(context), patch_kwargs
        )
    elif res.get('url_type') in p.toolkit.h.datastore_rw_resource_url_types():
        _schedule_patch_resource_last_modified(resource_id)

    result.pop('id', None)
    result.pop('connection_url', None)
    if not data_dict.pop('include_deleted_records', False):
        result.pop('deleted_records', None)
    return result


def datastore_records_delete(context: Context, data_dict: dict[str, Any]):
    '''Deletes records from a DataStore table but will never remove the table itself.

    :param resource_id: resource id that the data will be deleted from.
                        (required)
    :type resource_id: string
    :param force: set to True to edit a read-only resource
    :type force: bool (optional, default: False)
    :param filters: :ref:`filters` to apply before deleting (eg {"name": "fred"}).
                   If {} delete all records.
                   (required)
    :type filters: dictionary
    :param include_deleted_records: return the full values of deleted records
                                    (optional, default: False)
    :type include_deleted_records: bool
    :param calculate_record_count: False: don't update the count, True: update
        the count immediately, "background": schedule a background job to update
        the record count. The stored count of records is used to optimize
        datastore_search total count response. If doing a series of requests to
        change a resource, set this to False for all but the last request.
        (optional, default: "background")
    :type calculate_record_count: True, False or "background"

    For writable tables the resource ``last_modified`` value will be updated
    by a scheduled background job. See :ref:`background jobs` for more
    information.

    **Results:**

    :returns: Original filters sent.
    :rtype: dictionary

    '''
    schema = context.get('schema', dsschema.datastore_records_delete_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)
    return p.toolkit.get_action('datastore_delete')(context, data_dict)


@logic.side_effect_free
def datastore_search(context: Context, data_dict: dict[str, Any]):
    '''Search a DataStore resource.

    The datastore_search action allows you to search data in a resource. By
    default 100 rows are returned - see the `limit` parameter for more info.

    A DataStore resource that belongs to a private CKAN resource can only be
    read by you if you have access to the CKAN resource and send the
    appropriate authorization.

    :param resource_id: id or alias of the resource to be searched against
    :type resource_id: string
    :param filters: :ref:`filters` for matching conditions to select, e.g
                    {"key1": "a", "key2": "b"} (optional)
    :type filters: dictionary
    :param q: full text query. If it's a string, it'll search on all fields on
              each row. If it's a dictionary as {"key1": "a", "key2": "b"},
              it'll search on each specific field (optional)
    :type q: string or dictionary
    :param full_text: full text query. It search on all fields on each row.
                      This should be used in replace of ``q`` when performing
                      string search accross all fields
    :type full_text: string
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
                 e.g.: "fieldname1, fieldname2 desc nulls last"
    :type sort: string
    :param include_total: True to return total matching record count
                          (optional, default: true)
    :type include_total: bool
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
def datastore_search_sql(context: Context, data_dict: dict[str, Any]):
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

    .. note:: This action is not available by default and needs to be enabled
        with the :ref:`ckan.datastore.sqlsearch.enabled` setting.

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

    def check_access(table_names: list[str]):
        '''
        Raise NotAuthorized if current user is not allowed to access
        any of the tables passed

        :type table_names: list strings
        '''
        p.toolkit.check_access(
            'datastore_search_sql',
            Context(context, table_names=table_names),
            data_dict)

    result = backend.search_sql(
        Context(context, check_access=check_access),
        data_dict)
    result.pop('id', None)
    result.pop('connection_url', None)
    return result


def _check_read_only(res: dict[str, Any]):
    ''' Raises exception if the resource is read-only.
    Make sure the resource id is in resource_id
    '''
    if res.get('url_type') not in (
            p.toolkit.h.datastore_rw_resource_url_types()
        ):
        raise p.toolkit.ValidationError({
            'read-only': ['Cannot edit read-only resource because changes '
                          'made may be lost. Use a resource created for '
                          'editing e.g. with datastore_create or use '
                          '"force=True" to ignore this warning.']
        })


def _cancel_patch_resource_last_modified(resource_id: str):
    ''' Remove any existing scheduled job to patch resource
    last_modified.
    '''
    job_id = f'{resource_id} datastore patch last_modified'
    try:
        existing_job = p.toolkit.job_from_id(job_id)
    except KeyError:
        return
    existing_job.delete()


def _schedule_patch_resource_last_modified(resource_id: str):
    ''' Schedule a job to patch resource last_modified after a short
    time, but first cancel any existing job to do the same. This way
    metadata updates are minimized when there are sequential calls to
    datastore_create, datastore_upsert and/or datastore_delete.
    '''
    last_modified = datetime.now(timezone.utc)
    job_id = f'{resource_id} datastore patch last_modified'

    _cancel_patch_resource_last_modified(resource_id)
    p.toolkit.get_job_queue().enqueue_in(
        RESOURCE_LAST_MODIFIED_SETTLE_TIME,
        _patch_resource_last_modified,
        resource_id,
        last_modified,
        job_id=job_id,
    )


def _patch_resource_last_modified(resource_id: str, last_modified: datetime):
    ''' Job to patch a resource's last_modified value using the site user
    to prevent the creation of an activity record.
    '''
    site_user = p.toolkit.get_action('get_site_user')(
        {'ignore_auth': True}, {}
    )
    p.toolkit.get_action('resource_patch')(
        {'user': site_user['name'], 'ignore_auth': True},
        {'id': resource_id, 'last_modified': last_modified},
    )

def _cancel_calculate_record_count(resource_id: str) -> bool:
    job_id = f'{resource_id} calculate record count'
    try:
        existing_job = p.toolkit.job_from_id(job_id)
    except KeyError:
        return False
    existing_job.delete()
    return True

def _schedule_calculate_record_count(resource_id: str):
    job_id = f'{resource_id} calculate record count'
    delay = timedelta(seconds=p.toolkit.config[
        'ckan.datastore.background_calculate_record_count_delay'])

    p.toolkit.get_job_queue().enqueue_in(
        delay,
        _calculate_record_count,
        resource_id,
        job_id=job_id,
    )

def _calculate_record_count(resource_id: str):
    backend = DatastoreBackend.get_active_backend()
    backend.calculate_record_count(resource_id)


@logic.validate(dsschema.datastore_function_create_schema)
def datastore_function_create(context: Context, data_dict: dict[str, Any]):
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
def datastore_function_delete(context: Context, data_dict: dict[str, Any]):
    u'''
    Delete a trigger function

    :param name: function name
    :type name: string
    '''
    p.toolkit.check_access('datastore_function_delete', context, data_dict)
    backend = DatastoreBackend.get_active_backend()
    backend.drop_function(data_dict['name'], data_dict['if_exists'])
