import logging
import pylons
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


def datastore_delete(context, data_dict):
    '''Adds a new table to the datastore.

    :param resource_id: resource id that the data is going to be stored under.
    :type resource_id: string
    :param filter: Filter to do deleting on over eg {'name': 'fred'} if missing 
    delete whole table

    :returns: original filters sent.
    :rtype: dictionary

    '''
    model = _get_or_bust(context, 'model')

    _check_access('datastore_delete', context, data_dict)

    _get_or_bust(data_dict, 'resource_id')

    data_dict['connection_url'] = pylons.config['ckan.datastore_write_url']

    return db.delete(context, data_dict)
