import logging
import pylons
import ckan.logic as logic
import ckan.logic.action
import ckan.lib.dictization
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
    _get_or_bust(context, 'model')
    _get_or_bust(data_dict, 'resource_id')
    # TODO: check that resource_id exists in database

    _check_access('datastore_create', context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore_write_url']

    result = db.create(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result
