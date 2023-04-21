# encoding: utf-8
from ckan.plugins.toolkit import get_action, chained_action

from ckanext.tabledesigner.datastore import create_table


@chained_action
def resource_create(original_action, context, data_dict):
    _tabledesigner_info = data_dict.pop('_tabledesigner_info', None)
    res = original_action(context, data_dict)
    _create_table_and_view(res, _tabledesigner_info)
    return res


@chained_action
def resource_update(original_action, context, data_dict):
    res = original_action(context, data_dict)
    res = _create_table_and_view(res)
    return res


def _create_table_and_view(res, info=None):
    if res.get('url_type') != 'tabledesigner':
        return
    if not res.get('datastore_active'):
        create_table(res['id'], [] if info is None else info)

    views = get_action('resource_view_list')({}, {
        'id': res['id']
    })
    if any(v['view_type'] == 'datatables_view' for v in views):
        return
    get_action('resource_view_create')({}, {
        'resource_id': res['id'],
        'view_type': 'datatables_view',
        'title': 'Table Designer',
    })
