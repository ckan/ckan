# encoding: utf-8

from ckan.types import AuthResult, Context, DataDict
import ckan.plugins as p


def datastore_auth(context: Context,
                   data_dict: DataDict,
                   privilege: str = 'resource_update') -> AuthResult:
    if 'id' not in data_dict:
        data_dict['id'] = data_dict.get('resource_id')

    user = context.get('user')

    authorized = p.toolkit.check_access(privilege, context, data_dict)
    if not authorized:
        return {
            'success': False,
            'msg': p.toolkit._(
                'User {0} not authorized to update resource {1}'
                    .format(str(user), data_dict['id'])
            )
        }
    else:
        return {'success': True}


def datastore_create(context: Context, data_dict: DataDict):
    if 'resource' in data_dict and data_dict['resource'].get('package_id'):
        data_dict['id'] = data_dict['resource'].get('package_id')
        privilege = 'package_update'
    else:
        privilege = 'resource_update'

    return datastore_auth(context, data_dict, privilege=privilege)


def datastore_upsert(context: Context, data_dict: DataDict):
    return datastore_auth(context, data_dict)


def datastore_delete(context: Context, data_dict: DataDict):
    return datastore_auth(context, data_dict)


@p.toolkit.auth_allow_anonymous_access
def datastore_info(context: Context, data_dict: DataDict):
    return datastore_auth(context, data_dict, 'resource_show')


@p.toolkit.auth_allow_anonymous_access
def datastore_search(context: Context, data_dict: DataDict):
    return datastore_auth(context, data_dict, 'resource_show')


@p.toolkit.auth_allow_anonymous_access
def datastore_search_sql(context: Context, data_dict: DataDict) -> AuthResult:
    '''need access to view all tables in query'''

    for name in context['table_names']:
        name_auth = datastore_auth(
            context.copy(),  # required because check_access mutates context
            {'id': name},
            'resource_show')
        if not name_auth['success']:
            return {
                'success': False,
                'msg': 'Not authorized to read resource.'}
    return {'success': True}


def datastore_change_permissions(
        context: Context, data_dict: DataDict) -> AuthResult:
    return datastore_auth(context, data_dict)


def datastore_function_create(
        context: Context, data_dict: DataDict) -> AuthResult:
    '''sysadmin-only: functions can be used to skip access checks'''
    return {'success': False}


def datastore_function_delete(
        context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': False}


def datastore_run_triggers(
        context: Context, data_dict: DataDict) -> AuthResult:
    '''sysadmin-only: functions can be used to skip access checks'''
    return {'success': False}


def datastore_analyze(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': False}
