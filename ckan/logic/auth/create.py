# encoding: utf-8

from typing import Optional

import ckan.logic as logic
import ckan.authz as authz
import ckan.logic.auth as logic_auth

from ckan.common import _
from ckan.types import Context, DataDict, AuthResult

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


def file_upload(context: Context,
                data_dict: Optional[DataDict] = None) -> AuthResult:
    user = context['user']
    if authz.auth_is_anon_user(context):
        return {'success': False, 'msg': _(
            'User %s not authorized to create packages') % user}
    return {'success': True}


def resource_create(context: Context, data_dict: DataDict) -> AuthResult:
    model = context['model']
    user = context.get('user')

    package_id = data_dict.get('package_id')
    if not package_id and data_dict.get('id'):
        # This can happen when auth is deferred, eg from `resource_view_create`
        resource = logic_auth.get_resource_object(context, data_dict)
        package_id = resource.package_id

    if not package_id:
        raise logic.NotFound(
            _('No dataset id provided, cannot check auth.')
        )

    # check authentication against package
    pkg = model.Package.get(package_id)
    if not pkg:
        raise logic.NotFound(
            _('No package found for this resource, cannot check auth.')
        )

    pkg_dict = {'id': pkg.id}
    authorized = authz.is_authorized(
        'package_update', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False,
                'msg': _(
                    'User %s not authorized to create resources on dataset %s'
                ) % (str(user), package_id)}
    else:
        return {'success': True}


def resource_view_create(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized(
        'resource_create', context, {'id': data_dict['resource_id']})


def resource_create_default_resource_views(context: Context,
                                           data_dict: DataDict) -> AuthResult:
    return authz.is_authorized(
        'resource_create', context, {'id': data_dict['resource']['id']})


def package_create_default_resource_views(context: Context,
                                          data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_update', context,
                               data_dict['package'])


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


def group_create(context: Context,
                 data_dict: Optional[DataDict] = None) -> AuthResult:
    user = context['user']
    user = authz.get_user_id_for_username(user, allow_none=True)

    if user and authz.check_config_permission('user_create_groups'):
        return {'success': True}
    return {'success': False,
            'msg': _('User %s not authorized to create groups') % user}


def organization_create(context: Context,
                        data_dict: Optional[DataDict] = None) -> AuthResult:
    user = context['user']
    user = authz.get_user_id_for_username(user, allow_none=True)

    if user and authz.check_config_permission('user_create_organizations'):
        return {'success': True}
    return {'success': False,
            'msg': _('User %s not authorized to create organizations') % user}


@logic.auth_allow_anonymous_access
def user_create(context: Context,
                data_dict: Optional[DataDict] = None) -> AuthResult:
    using_api = 'api_version' in context
    create_user_via_api = authz.check_config_permission(
            'create_user_via_api')
    create_user_via_web = authz.check_config_permission(
            'create_user_via_web')

    if using_api and not create_user_via_api:
        return {'success': False, 'msg': _('User {user} not authorized to '
            'create users via the API').format(user=context.get('user'))}
    if not using_api and not create_user_via_web:
        return {'success': False, 'msg': _('Not authorized to '
            'create users')}
    return {'success': True}


def user_invite(context: Context, data_dict: DataDict) -> AuthResult:
    data_dict['id'] = data_dict['group_id']
    return group_member_create(context, data_dict)


def _check_group_auth(context: Context, data_dict: Optional[DataDict]) -> bool:
    '''Has this user got update permission for all of the given groups?
    If there is a package in the context then ignore that package's groups.
    (owner_org is checked elsewhere.)
    :returns: False if not allowed to update one (or more) of the given groups.
              True otherwise. i.e. True is the default. A blank data_dict
              mentions no groups, so it returns True.

    '''
    # FIXME This code is shared amoung other logic.auth files and should be
    # somewhere better
    if not data_dict:
        return True

    model = context['model']
    user = context['user']
    pkg = context.get("package")

    group_blobs = data_dict.get('groups', [])
    groups = set()
    for group_blob in group_blobs:
        # group_blob might be a dict or a group_ref
        if isinstance(group_blob, dict):
            # use group id by default, but we can accept name as well
            id = group_blob.get('id') or group_blob.get('name')
            if not id:
                continue
        else:
            id = group_blob
        grp = model.Group.get(id)
        if grp is None:
            raise logic.NotFound(_('Group was not found.'))
        groups.add(grp)

    if pkg:
        pkg_groups = pkg.get_groups()

        groups = groups - set(pkg_groups)

    for group in groups:
        if not authz.has_user_permission_for_group_or_org(
                group.id, user, 'manage_group'):
            return False

    return True


def vocabulary_create(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}


def tag_create(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}


def _group_or_org_member_create(context: Context,
                                data_dict: DataDict) -> AuthResult:
    user = context['user']
    group_id = data_dict['id']
    if not authz.has_user_permission_for_group_or_org(
            group_id, user, 'membership'):
        return {'success': False,
                'msg': _('User %s not authorized to add members') % user}
    return {'success': True}


def organization_member_create(context: Context,
                               data_dict: DataDict) -> AuthResult:
    return _group_or_org_member_create(context, data_dict)


def group_member_create(context: Context, data_dict: DataDict) -> AuthResult:
    return _group_or_org_member_create(context, data_dict)


def member_create(context: Context, data_dict: DataDict) -> AuthResult:
    group = logic_auth.get_group_object(context, data_dict)
    user = context['user']

    # User must be able to update the group to add a member to it
    permission = 'update'
    # However if the user is member of group then they can add/remove datasets
    if not group.is_organization and data_dict.get('object_type') == 'package':
        permission = 'manage_group'

    authorized = authz.has_user_permission_for_group_or_org(group.id,
                                                                user,
                                                                permission)
    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit group %s') %
                        (str(user), group.id)}
    else:
        return {'success': True}


def api_token_create(context: Context, data_dict: DataDict) -> AuthResult:
    """Create new token for current user.
    """
    user = context['model'].User.get(data_dict['user'])
    assert user
    return {'success': user.name == context['user']}



def package_collaborator_create(context: Context,
                                data_dict: DataDict) -> AuthResult:
    '''Checks if a user is allowed to add collaborators to a dataset

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
            'msg': _('User %s not authorized to add'
                     ' collaborators to this dataset') % user}

    return {'success': True}
