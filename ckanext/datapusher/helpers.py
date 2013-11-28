import ckan.plugins.toolkit as toolkit


def datapusher_status(resource_id):
    try:
        return toolkit.get_action('datapusher_status')(
            {}, {'resource_id': resource_id})
    except toolkit.ObjectNotFound:
        return {
            'status': 'unknown'
        }
