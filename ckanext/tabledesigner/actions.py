# encoding: utf-8
from ckan.plugins.toolkit import get_action, chained_action


@chained_action
def resource_create(original_action, context, data_dict):
    _tabledesigner_info = data_dict.pop('_tabledesigner_info', None)
    res = original_action(context, data_dict)
    _create_datastore_table(res, _tabledesigner_info)
    return res


@chained_action
def resource_update(original_action, context, data_dict):
    res = original_action(context, data_dict)
    _create_datastore_table(res)
    return pkg


def _create_datastore_table(res, info=None):
    if res.get('url_type') != 'tabledesigner':
        return
    if res.get('datastore_active'):
        return
    get_action('datastore_create')({}, {
        'resource_id': res['id'],
        'force': True,  # required because url_type != datastore
        'fields': info or [],
    })
