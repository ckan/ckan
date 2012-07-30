import logging
import pylons
import ckan.logic as logic
import ckan.plugins as p
import ckanext.datastore.db as db

log = logging.getLogger(__name__)
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
    id = _get_or_bust(data_dict, 'resource_id')

    if not model.Resource.get(id):
        raise p.toolkit.ObjectNotFound(p.toolkit._(
            'Resource "{}" was not found.'.format(id)
        ))

    p.toolkit.check_access('datastore_create', context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore_write_url']

    result = db.create(context, data_dict)
    result.pop('id')
    result.pop('connection_url')
    return result
