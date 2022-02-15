# encoding: utf-8

import ckan.logic as logic
import ckan.authz as authz
from ckan.logic.auth import get_group_object
from ckan.logic.auth import get_resource_object
from ckan.common import _
from ckan.types import Context, DataDict, AuthResult


def user_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}


def package_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # Defer authorization for package_delete to package_update, as deletions
    # are essentially changing the state field
    return authz.is_authorized('package_update', context, data_dict)


def dataset_purge(context: Context, data_dict: DataDict) -> AuthResult:
    # Only sysadmins are authorized to purge datasets
    return {'success': False}


def resource_delete(context: Context, data_dict: DataDict) -> AuthResult:
    model = context['model']
    user = context.get('user')
    resource = get_resource_object(context, data_dict)

    # check authentication against package
    assert resource.package_id
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(_(
            'No package found for this resource, cannot check auth.'))

    pkg_dict = {'id': pkg.id}
    authorized = authz.is_authorized(
        'package_delete', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _(
            'User %s not authorized to delete resource %s'
        ) % (user, resource.id)}
    else:
        return {'success': True}


def resource_view_delete(context: Context, data_dict: DataDict) -> AuthResult:
    model = context['model']

    resource_view = model.ResourceView.get(data_dict['id'])
    if not resource_view:
        raise logic.NotFound(_('Resource view not found, cannot check auth.'))
    resource_id = resource_view.resource_id

    return authz.is_authorized('resource_delete', context, {'id': resource_id})


def resource_view_clear(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}


def package_relationship_delete(context: Context,
                                data_dict: DataDict) -> AuthResult:
    user = context['user']
    relationship = context['relationship']

    # If you can create this relationship the you can also delete it
    authorized = authz.is_authorized_boolean(
        'package_relationship_create', context, data_dict)
    if not authorized:
        return {'success': False, 'msg': _(
            'User %s not authorized to delete relationship %s'
        ) % (user ,relationship.id)}
    else:
        return {'success': True}

def group_delete(context: Context, data_dict: DataDict) -> AuthResult:
    group = get_group_object(context, data_dict)
    user = context['user']
    if not authz.check_config_permission('user_delete_groups'):
        return {'success': False,
            'msg': _('User %s not authorized to delete groups') % user}
    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'delete')
    if not authorized:
        return {'success': False, 'msg': _(
            'User %s not authorized to delete group %s') % (user ,group.id)}
    else:
        return {'success': True}

def group_purge(context: Context, data_dict: DataDict) -> AuthResult:
    # Only sysadmins are authorized to purge groups.
    return {'success': False}

def organization_purge(context: Context, data_dict: DataDict) -> AuthResult:
    # Only sysadmins are authorized to purge organizations.
    return {'success': False}

def organization_delete(context: Context, data_dict: DataDict) -> AuthResult:
    group = get_group_object(context, data_dict)
    user = context['user']
    if not authz.check_config_permission('user_delete_organizations'):
        return {'success': False,
            'msg': _('User %s not authorized to delete organizations') % user}
    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'delete')
    if not authorized:
        return {'success': False, 'msg': _(
            'User %s not authorized to delete organization %s'
        ) % (user ,group.id)}
    else:
        return {'success': True}


def task_status_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}


def vocabulary_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}

def tag_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}

def group_member_delete(context: Context, data_dict: DataDict) -> AuthResult:
    ## just return true as logic runs through member_delete
    return {'success': True}


def organization_member_delete(context: Context,
                               data_dict: DataDict) -> AuthResult:
    ## just return true as logic runs through member_delete
    return {'success': True}

def member_delete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('member_create', context, data_dict)


def package_collaborator_delete(context: Context,
                                data_dict: DataDict) -> AuthResult:
    '''Checks if a user is allowed to remove collaborators from a dataset

    See :py:func:`~ckan.authz.can_manage_collaborators` for details
    '''
    user = context['user']
    model = context['model']

    pkg = model.Package.get(data_dict['id'])
    user_obj = model.User.get(user)

    assert pkg and user_obj
    if not authz.can_manage_collaborators(pkg.id, user_obj.id):
        return {
            'success': False,
            'msg': _('User %s not authorized to remove'
                     ' collaborators from this dataset') % user}

    return {'success': True}


def job_clear(context: Context, data_dict: DataDict) -> AuthResult:
    '''Clear background jobs. Only sysadmins.'''
    return {'success': False}


def job_cancel(context: Context, data_dict: DataDict) -> AuthResult:
    '''Cancel a background job. Only sysadmins.'''
    return {'success': False}


def api_token_revoke(context: Context, data_dict: DataDict) -> AuthResult:
    """Delete token.
    """
    if authz.auth_is_anon_user(context):
        return {u'success': False}

    model = context[u'model']
    token = model.ApiToken.get(data_dict[u'jti'])
    # Do not make distinction between absent keys and keys not owned
    # by user in order to prevent accidential key discovery.
    if token is None or token.owner and token.owner.name != context[u'user']:
        return {u'success': False}
    return {u'success': True}
