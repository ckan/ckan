# encoding: utf-8

import ckan.logic as logic
import ckan.authz as authz
from ckan import model
from ckan.common import _, config
from ckan.logic.auth import (get_package_object, get_group_object,
                             get_resource_object,
                             restrict_anon)
from ckan.lib.plugins import get_permission_labels
from ckan.common import asbool
from ckan.types import Context, DataDict, AuthResult


def sysadmin(context: Context, data_dict: DataDict) -> AuthResult:
    ''' This is a pseudo check if we are a sysadmin all checks are true '''
    return {'success': False, 'msg': _('Not authorized')}


def group_list_available(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('group_list', context, data_dict)


def _followee_list(context: Context, data_dict: DataDict) -> AuthResult:
    # Visitors cannot see what users are following.
    authorized_user = model.User.get(context.get('user'))
    if not authorized_user:
        return {'success': False, 'msg': _('Not authorized')}

    # Any user is authorized to see what she herself is following.
    requested_user = model.User.get(data_dict.get('id', ''))
    if authorized_user == requested_user:
        return {'success': True}

    # Sysadmins are authorized to see what anyone is following.
    return authz.is_authorized('sysadmin', context, data_dict)


def user_reset(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}


def request_reset(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}
