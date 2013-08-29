import ckan.logic as logic
import ckan.new_authz as new_authz

from ckan.common import _


def package_create(context, data_dict=None):
    user = context['user']

    if new_authz.auth_is_anon_user(context):
        check1 = new_authz.check_config_permission('anon_create_dataset')
    else:
        check1 = new_authz.check_config_permission('create_dataset_if_not_in_organization') \
            or new_authz.check_config_permission('create_unowned_dataset') \
            or new_authz.has_user_permission_for_some_org(user, 'create_dataset')

    if not check1:
        return {'success': False, 'msg': _('User %s not authorized to create packages') % user}

    check2 = _check_group_auth(context,data_dict)
    if not check2:
        return {'success': False, 'msg': _('User %s not authorized to edit these groups') % user}

    # If an organization is given are we able to add a dataset to it?
    data_dict = data_dict or {}
    org_id = data_dict.get('organization_id')
    if org_id and not new_authz.has_user_permission_for_group_or_org(
            org_id, user, 'create_dataset'):
        return {'success': False, 'msg': _('User %s not authorized to add dataset to this organization') % user}
    return {'success': True}


def file_upload(context, data_dict=None):
    user = context['user']
    if new_authz.auth_is_anon_user(context):
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
    # resource_create runs through package_update, no need to
    # check users eligibility to add resource to package here.

    # FIXME This is identical behaviour to what existed but feels like we
    # should be using package_update permissions and have better errors.  I
    # am also not sure about the need for the group issue
    return new_authz.is_authorized('package_create', context, data_dict)

def package_relationship_create(context, data_dict):
    user = context['user']

    id = data_dict['subject']
    id2 = data_dict['object']

    # If we can update each package we can see the relationships
    authorized1 = new_authz.is_authorized_boolean(
        'package_update', context, {'id': id})
    authorized2 = new_authz.is_authorized_boolean(
        'package_update', context, {'id': id2})

    if not authorized1 and authorized2:
        return {'success': False, 'msg': _('User %s not authorized to edit these packages') % user}
    else:
        return {'success': True}

def group_create(context, data_dict=None):
    user = context['user']
    user = new_authz.get_user_id_for_username(user, allow_none=True)

    if user and new_authz.check_config_permission('user_create_groups'):
        return {'success': True}
    return {'success': False,
            'msg': _('User %s not authorized to create groups') % user}


def organization_create(context, data_dict=None):
    user = context['user']
    user = new_authz.get_user_id_for_username(user, allow_none=True)

    if user and new_authz.check_config_permission('user_create_organizations'):
        return {'success': True}
    return {'success': False,
            'msg': _('User %s not authorized to create organizations') % user}

def rating_create(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def user_create(context, data_dict=None):
    user = context['user']

    if ('api_version' in context
            and not new_authz.check_config_permission('create_user_via_api')):
        return {'success': False, 'msg': _('User %s not authorized to create users') % user}
    else:
        return {'success': True}


def _check_group_auth(context, data_dict):
    # FIXME This code is shared amoung other logic.auth files and should be
    # somewhere better
    if not data_dict:
        return True

    model = context['model']
    user = context['user']
    pkg = context.get("package")

    api_version = context.get('api_version') or '1'

    group_blobs = data_dict.get("groups", [])
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
        if not new_authz.has_user_permission_for_group_or_org(group.id, user, 'update'):
            return False

    return True

## Modifications for rest api

def package_create_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if user in (model.PSEUDO_USER__VISITOR, ''):
        return {'success': False, 'msg': _('Valid API key needed to create a package')}

    return package_create(context, data_dict)

def group_create_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if user in (model.PSEUDO_USER__VISITOR, ''):
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
    if not new_authz.has_user_permission_for_group_or_org(group_id, user, 'membership'):
        return {'success': False, 'msg': _('User %s not authorized to add members') % user}
    return {'success': True}

def organization_member_create(context, data_dict):
    return _group_or_org_member_create(context, data_dict)

def group_member_create(context, data_dict):
    return _group_or_org_member_create(context, data_dict)
