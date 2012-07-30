import logging
import pylons
import ckan.logic as logic
import ckan.plugins as p
import ckanext.datastore.db as db

log = logging.getLogger(__name__)
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
    model = _get_or_bust(context, 'model')
    id = _get_or_bust(data_dict, 'resource_id')

    if not model.Resource.get(id):
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            'Resource "{}" was not found.'.format(id)
        ))

    p.toolkit.check_access('datastore_delete', context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore_write_url']

    result = db.delete(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result
