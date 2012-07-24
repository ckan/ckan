import logging
import ckan.logic as logic
import ckan.logic.action
import ckan.lib.dictization
import ckan.plugins as p
import ckanext.datastore.logic.schema
import ckanext.datastore.db as db

log = logging.getLogger(__name__)

_validate = ckan.lib.navl.dictization_functions.validate
_check_access = logic.check_access
_get_or_bust = logic.get_or_bust


def datastore_create(context, data_dict):
    '''Adds a new table to the datastore.

    :param resource_id: resource id that the data is going to be stored under.
    :type resource_id: string
    :param fields: fields/columns and their extra metadata.
    :type fields: list of dictionaries
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ['a', b']}]
    :type records: list of dictionaries

    :returns: the newly created data object.
    :rtype: dictionary

    '''
    model = _get_or_bust(context, 'model')
    resource_id = _get_or_bust(data_dict, 'resource_id')
    fields = data_dict.get('fields')
    records = data_dict.get('records')

    _check_access('datastore_create', context, data_dict)

    schema = ckanext.datastore.logic.schema.default_datastore_create_schema()
    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise p.toolkit.ValidationError(errors)

    return db.create(resource_id, fields, records)
