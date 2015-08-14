import ckan.logic as logic
import ckan.authz as authz
import ckan.logic.auth as logic_auth

from ckan.common import _

@logic.auth_allow_anonymous_access
def package_create(context, data_dict=None):
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
        return {'success': False, 'msg': _('User %s not authorized to create packages') % user}

    check2 = _check_group_auth(context,data_dict)
    if not check2:
        return {'success': False, 'msg': _('User %s not authorized to edit these groups') % user}

    # If an organization is given are we able to add a dataset to it?
    data_dict = data_dict or {}
    org_id = data_dict.get('owner_org')
    if org_id and not authz.has_user_permission_for_group_or_org(
            org_id, user, 'create_dataset'):
        return {'success': False, 'msg': _('User %s not authorized to add dataset to this organization') % user}
    return {'success': True}


def file_upload(context, data_dict=None):
    user = context['user']
    if authz.auth_is_anon_user(context):
        return {'success': False, 'msg': _('User %s not authorized to create packages') % user}
    return {'success': True}

def related_create(context, data_dict=None):
    '''Users must be logged-in to create related items.

    To create a featured item the user must be a sysadmin.
    '''
    model = context['model']
    user = context['user']
    userobj = model.User.get( user )

    if userobj:
        if data_dict.get('featured', 0) != 0:
            return {'success': False,
                    'msg': _('You must be a sysadmin to create a featured '
                             'related item')}
        return {'success': True}

    return {'success': False, 'msg': _('You must be logged in to add a related item')}


def resource_create(context, data_dict):
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
    authorized = authz.is_authorized('package_update', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to create resources on dataset %s') %
                        (str(user), package_id)}
    else:
        return {'success': True}


def resource_view_create(context, data_dict):
    return resource_create(context, {'id': data_dict['resource_id']})


def resource_create_default_resource_views(context, data_dict):
    return resource_create(context, {'id': data_dict['resource']['id']})


def package_create_default_resource_views(context, data_dict):
    return authz.is_authorized('package_update', context,
                               data_dict['package'])


def package_relationship_create(context, data_dict):
    user = context['user']

    id = data_dict['subject']
    id2 = data_dict['object']

    # If we can update each package we can see the relationships
    authorized1 = authz.is_authorized_boolean(
        'package_update', context, {'id': id})
    authorized2 = authz.is_authorized_boolean(
        'package_update', context, {'id': id2})

    if not authorized1 and authorized2:
        return {'success': False, 'msg': _('User %s not authorized to edit these packages') % user}
    else:
        return {'success': True}

def group_create(context, data_dict=None):
    user = context['user']
    user = authz.get_user_id_for_username(user, allow_none=True)

    if user and authz.check_config_permission('user_create_groups'):
        return {'success': True}
    return {'success': False,
            'msg': _('User %s not authorized to create groups') % user}


def organization_create(context, data_dict=None):
    user = context['user']
    user = authz.get_user_id_for_username(user, allow_none=True)

    if user and authz.check_config_permission('user_create_organizations'):
        return {'success': True}
    return {'success': False,
            'msg': _('User %s not authorized to create organizations') % user}

def rating_create(context, data_dict):
    # No authz check in the logic function
    return {'success': True}


@logic.auth_allow_anonymous_access
def user_create(context, data_dict=None):
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

def user_invite(context, data_dict):
    data_dict['id'] = data_dict['group_id']
    return group_member_create(context, data_dict)

def _check_group_auth(context, data_dict):
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

    api_version = context.get('api_version') or '1'

    group_blobs = data_dict.get('groups', [])
    groups = set()
    for group_blob in group_blobs:
        # group_blob might be a dict or a group_ref
        if isinstance(group_blob, dict):
            if api_version == '1':
                id = group_blob.get('name')
            else:
                id = group_blob.get('id')
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
        if not authz.has_user_permission_for_group_or_org(group.id, user, 'update'):
            return False

    return True

## Modifications for rest api

def package_create_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if not user:
        return {'success': False, 'msg': _('Valid API key needed to create a package')}

    return package_create(context, data_dict)

def group_create_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if not user:
        return {'success': False, 'msg': _('Valid API key needed to create a group')}

    return group_create(context, data_dict)

def vocabulary_create(context, data_dict):
    # sysadmins only
    return {'success': False}

def activity_create(context, data_dict):
    # sysadmins only
    return {'success': False}

def tag_create(context, data_dict):
    # sysadmins only
    return {'success': False}

def _group_or_org_member_create(context, data_dict):
    user = context['user']
    group_id = data_dict['id']
    if not authz.has_user_permission_for_group_or_org(group_id, user, 'membership'):
        return {'success': False, 'msg': _('User %s not authorized to add members') % user}
    return {'success': True}

def organization_member_create(context, data_dict):
    return _group_or_org_member_create(context, data_dict)

def group_member_create(context, data_dict):
    return _group_or_org_member_create(context, data_dict)

def member_create(context, data_dict):
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
