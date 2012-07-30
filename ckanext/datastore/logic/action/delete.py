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


def datastore_delete(context, data_dict):
    '''Deletes a table from the datastore.

    :param resource_id: resource id that the data will be deleted from.
    :type resource_id: string
    :param filter: filter to do deleting on over (eg {'name': 'fred'}).
                   If missing delete whole table.

    :returns: original filters sent.
    :rtype: dictionary

    '''
    _get_or_bust(context, 'model')
    _get_or_bust(data_dict, 'resource_id')

    _check_access('datastore_delete', context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore_write_url']

    result = db.delete(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result
