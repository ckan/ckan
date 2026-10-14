from __future__ import annotations



from .create import _check_group_auth

from ckan import model

from ckan.common import _

from ckan.lib.plugins import get_permission_labels

from ckan.logic.auth import get_package_object

from ckan.types import AuthResult, Context, DataDict

from typing import Optional

import ckan.authz as authz

import ckan.logic as logic

import ckan.logic.auth as logic_auth





def package_search(context: Context, data_dict: DataDict) -> AuthResult:
    # Everyone can search by default
    return {'success': True}

def package_list(context: Context, data_dict: DataDict) -> AuthResult:
    # List of all active packages are visible by default
    return {'success': True}

def current_package_list_with_resources(context: Context,
                                        data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_list', context, data_dict)

def license_list(context: Context, data_dict: DataDict) -> AuthResult:
    # Licenses list is visible by default
    return {'success': True}

def package_relationships_list(context: Context,
                               data_dict: DataDict) -> AuthResult:
    user = context.get('user')

    id = data_dict['id']
    id2 = data_dict.get('id2')

    # If we can see each package we can see the relationships
    authorized1 = authz.is_authorized_boolean(
        'package_show', context, {'id': id})
    if id2:
        authorized2 = authz.is_authorized_boolean(
            'package_show', context, {'id': id2})
    else:
        authorized2 = True

    if not (authorized1 and authorized2):
        return {'success': False, 'msg': _('User %s not authorized to read these packages') % user}
    else:
        return {'success': True}

def package_show(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get('user')
    package = get_package_object(context, data_dict)
    labels = get_permission_labels()
    user_labels = labels.get_user_dataset_labels(context['auth_user_obj'])
    authorized = any(
        dl in user_labels for dl in labels.get_dataset_labels(package))

    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to read package %s') % (user, package.id)}
    else:
        return {'success': True}

def package_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_list', context, data_dict)

def package_collaborator_list(context: Context,
                              data_dict: DataDict) -> AuthResult:
    '''Checks if a user is allowed to list the collaborators from a dataset

    See :py:func:`~ckan.authz.can_manage_collaborators` for details
    '''
    user = context['user']

    pkg = model.Package.get(data_dict['id'])
    user_obj = model.User.get(user)

    assert pkg
    assert user_obj
    if not authz.can_manage_collaborators(pkg.id, user_obj.id):
        return {
            'success': False,
            'msg': _('User %s not authorized to list collaborators from this dataset') % user}

    return {'success': True}

def package_collaborator_list_for_user(context: Context,
                                       data_dict: DataDict) -> AuthResult:
    '''Checks if a user is allowed to list all datasets a user is a collaborator in

    The current implementation restricts to the own users themselves.
    '''
    user_obj = context.get('auth_user_obj')
    if user_obj and data_dict.get('id') in (user_obj.name, user_obj.id):
        return {'success': True}
    return {'success': False}

@logic.auth_allow_anonymous_access
def package_create(context: Context,
                   data_dict: Optional[DataDict] = None) -> AuthResult:
    user = context['user']

    if authz.auth_is_anon_user(context):
        check1 = all(authz.check_config_permission(p) for p in (
            'anon_create_dataset',
            'create_dataset_if_not_in_organization',
            'create_unowned_dataset',
            ))
    else:
        check1 = all(authz.check_config_permission(p) for p in (
            'create_dataset_if_not_in_organization',
            'create_unowned_dataset',
            )) or authz.has_user_permission_for_some_org(
            user, 'create_dataset')

    if not check1:
        return {'success': False, 'msg': _(
            'User %s not authorized to create packages') % user}

    check2 = _check_group_auth(context, data_dict)
    if not check2:
        return {'success': False, 'msg': _(
            'User %s not authorized to edit these groups') % user}

    # If an organization is given are we able to add a dataset to it?
    data_dict = data_dict or {}
    org_id = data_dict.get('owner_org')
    if org_id and not authz.has_user_permission_for_group_or_org(
            org_id, user, 'create_dataset'):
        return {'success': False, 'msg': _(
            'User %s not authorized to add dataset to this organization'
        ) % user}
    return {'success': True}

def package_relationship_create(context: Context,
                                data_dict: DataDict) -> AuthResult:
    user = context['user']

    id = data_dict['subject']
    id2 = data_dict['object']

    # If we can update each package we can see the relationships
    authorized1 = authz.is_authorized_boolean(
        'package_update', context, {'id': id})
    authorized2 = authz.is_authorized_boolean(
        'package_update', context, {'id': id2})

    if not (authorized1 and authorized2):
        return {'success': False, 'msg': _(
            'User %s not authorized to edit these packages') % user}
    else:
        return {'success': True}

def package_collaborator_create(context: Context,
                                data_dict: DataDict) -> AuthResult:
    '''Checks if a user is allowed to add collaborators to a dataset

    See :py:func:`~ckan.authz.can_manage_collaborators` for details
    '''
    user = context['user']

    pkg = model.Package.get(data_dict['id'])
    user_obj = model.User.get(user)
    assert pkg and user_obj
    if not authz.can_manage_collaborators(pkg.id, user_obj.id):
        return {
            'success': False,
            'msg': _('User %s not authorized to add'
                     ' collaborators to this dataset') % user}

    return {'success': True}

@logic.auth_allow_anonymous_access
def package_reindex(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_update', context, data_dict)

@logic.auth_allow_anonymous_access
def package_update(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get('user')

    package = logic_auth.get_package_object(context, data_dict)
    if package.owner_org:
        # if there is an owner org then we must have update_dataset
        # permission for that organization
        check1 = authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'update_dataset'
        )
    else:
        # If dataset is not owned then we can edit if config permissions allow
        if authz.auth_is_anon_user(context):
            check1 = all(authz.check_config_permission(p) for p in (
                'anon_create_dataset',
                'create_dataset_if_not_in_organization',
                'create_unowned_dataset',
                ))
        else:
            check1 = all(authz.check_config_permission(p) for p in (
                'create_dataset_if_not_in_organization',
                'create_unowned_dataset',
                )) or authz.has_user_permission_for_some_org(
                user, 'create_dataset')

    if not check1:
        success = False
        if authz.check_config_permission('allow_dataset_collaborators'):
            # if org-level auth failed, check dataset-level auth
            # (ie if user is a collaborator)
            user_obj = model.User.get(user)
            if user_obj:
                success = authz.user_is_collaborator_on_dataset(
                    user_obj.id, package.id, ['admin', 'editor'])
        if not success:
            return {'success': False,
                    'msg': _('User %s not authorized to edit package %s') %
                            (str(user), package.id)}
    else:
        check2 = _check_group_auth(context, data_dict)
        if not check2:
            return {'success': False,
                    'msg': _('User %s not authorized to edit these groups') %
                            (str(user))}

    return {'success': True}

def package_revise(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_update', context, data_dict['update'])

def package_relationship_update(context: Context,
                                data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_relationship_create',
                               context,
                               data_dict)

def package_owner_org_update(context: Context,
                             data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}

def bulk_update_private(context: Context, data_dict: DataDict) -> AuthResult:
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}

def bulk_update_public(context: Context, data_dict: DataDict) -> AuthResult:
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}

def bulk_update_delete(context: Context, data_dict: DataDict) -> AuthResult:
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}

def package_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # Defer authorization for package_delete to package_update, as deletions
    # are essentially changing the state field
    return authz.is_authorized('package_update', context, data_dict)

def dataset_purge(context: Context, data_dict: DataDict) -> AuthResult:
    # Only sysadmins are authorized to purge datasets
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

def package_collaborator_delete(context: Context,
                                data_dict: DataDict) -> AuthResult:
    '''Checks if a user is allowed to remove collaborators from a dataset

    See :py:func:`~ckan.authz.can_manage_collaborators` for details
    '''
    user = context['user']

    pkg = model.Package.get(data_dict['id'])
    user_obj = model.User.get(user)

    assert pkg and user_obj
    if not authz.can_manage_collaborators(pkg.id, user_obj.id):
        return {
            'success': False,
            'msg': _('User %s not authorized to remove'
                     ' collaborators from this dataset') % user}

    return {'success': True}

def package_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_update', context, data_dict)
