# encoding: utf-8
from ckan.plugins.toolkit import get_action, chained_action

from ckanext.tabledesigner.datastore import create_table


@chained_action
def resource_create(original_action, context, data_dict):
    res = original_action(context, data_dict)
    _create_table_and_view(res)
    return res


@chained_action
def resource_update(original_action, context, data_dict):
    res = original_action(context, data_dict)
    res = _create_table_and_view(res)
    return res


def _create_table_and_view(res):
    if res.get('url_type') != 'tabledesigner':
        return
    if not res.get('datastore_active'):
        create_table(res['id'], [])

    views = get_action('resource_view_list')({}, {
        'id': res['id']
    })
    if any(v['view_type'] == 'datatables_view' for v in views):
        return
    get_action('resource_view_create')({}, {
        'resource_id': res['id'],
        'view_type': 'datatables_view',
        'title': 'Table',
    })
