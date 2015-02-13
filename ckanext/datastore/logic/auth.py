import ckan.plugins as p


def datastore_auth(context, data_dict, privilege='resource_update'):
    if not 'id' in data_dict:
        data_dict['id'] = data_dict.get('resource_id')

    user = context.get('user')

    authorized = p.toolkit.check_access(privilege, context, data_dict)

    if not authorized:
        return {
            'success': False,
            'msg': p.toolkit._('User {0} not authorized to update resource {1}'
                    .format(str(user), data_dict['id']))
        }
    else:
        return {'success': True}


def datastore_create(context, data_dict):

    if 'resource' in data_dict and data_dict['resource'].get('package_id'):
        data_dict['id'] = data_dict['resource'].get('package_id')
        privilege = 'package_update'
    else:
        privilege = 'resource_update'

    return datastore_auth(context, data_dict, privilege=privilege)


def datastore_upsert(context, data_dict):
    return datastore_auth(context, data_dict)


def datastore_delete(context, data_dict):
    return datastore_auth(context, data_dict)


@p.toolkit.auth_allow_anonymous_access
def datastore_info(context, data_dict):
    return datastore_auth(context, data_dict, 'resource_show')


@p.toolkit.auth_allow_anonymous_access
def datastore_search(context, data_dict):
    return datastore_auth(context, data_dict, 'resource_show')


@p.toolkit.auth_allow_anonymous_access
def datastore_search_sql(context, data_dict):
    return {'success': True}


def datastore_change_permissions(context, data_dict):
    return datastore_auth(context, data_dict)
