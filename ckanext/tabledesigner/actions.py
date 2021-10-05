from ckan.plugins.toolkit import get_action, chained_action


@chained_action
def package_create(original_action, context, data_dict):
    pkg = original_action(context, data_dict)
    _create_datastore_tables(pkg)
    return pkg


@chained_action
def package_update(original_action, context, data_dict):
    pkg = original_action(context, data_dict)
    _create_datastore_tables(pkg)
    return pkg


def _create_datastore_tables(pkg):
    for r in pkg['resources']:
        if r.get('url_type') != 'table_designer':
            continue
        if r.get('datastore_active'):
            continue
        get_action('datastore_create')({}, {
            'resource_id': r['id'],
            'force': True,  # required because url_type != datastore
            'fields': [],
        })
