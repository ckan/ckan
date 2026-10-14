from __future__ import annotations



from .group import _group_or_org_member_create

from ckan.common import _

from ckan.logic.auth import get_group_object

from ckan.types import AuthResult, Context, DataDict

from typing import Optional

import ckan.authz as authz

import ckan.logic.auth as logic_auth





def organization_list(context: Context, data_dict: DataDict) -> AuthResult:
    # List of all active organizations are visible by default
    return {'success': True}

def organization_list_for_user(context: Context,
                               data_dict: DataDict) -> AuthResult:
    return {'success': True}

def organization_show(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('group_show', context, data_dict)

def organization_autocomplete(context: Context,
                              data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('organization_list', context, data_dict)

def organization_create(context: Context,
                        data_dict: Optional[DataDict] = None) -> AuthResult:
    user = context['user']
    user = authz.get_user_id_for_username(user, allow_none=True)

    if user and authz.check_config_permission('user_create_organizations'):
        return {'success': True}
    return {'success': False,
            'msg': _('User %s not authorized to create organizations') % user}

def organization_member_create(context: Context,
                               data_dict: DataDict) -> AuthResult:
    return _group_or_org_member_create(context, data_dict)

def organization_update(context: Context, data_dict: DataDict) -> AuthResult:
    group = logic_auth.get_group_object(context, data_dict)
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')
    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit organization %s') %
                        (user, group.id)}
    else:
        return {'success': True}

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

def organization_member_delete(context: Context,
                               data_dict: DataDict) -> AuthResult:
    ## just return true as logic runs through member_delete
    return {'success': True}

def organization_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('organization_update', context, data_dict)
