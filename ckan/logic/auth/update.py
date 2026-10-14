# encoding: utf-8

import ckan.logic as logic
import ckan.authz as authz
import ckan.logic.auth as logic_auth
from ckan import model
from ckan.common import _

# FIXME this import is evil and should be refactored
from ckan.logic.auth.create import _check_group_auth
from ckan.types import Context, DataDict, AuthResult


def package_change_state(context: Context, data_dict: DataDict) -> AuthResult:
    user = context['user']
    package = logic_auth.get_package_object(context, data_dict)

    # use the logic for package_update
    authorized = authz.is_authorized_boolean('package_update',
                                             context,
                                             data_dict)
    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to change state of package %s') %
                    (str(user), package.id)
        }
    else:
        return {'success': True}


def group_change_state(context: Context, data_dict: DataDict) -> AuthResult:
    user = context['user']
    group = logic_auth.get_group_object(context, data_dict)

    # use logic for group_update
    authorized = authz.is_authorized_boolean('group_update',
                                             context,
                                             data_dict)
    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to change state of group %s') %
                    (str(user), group.id)
        }
    else:
        return {'success': True}


def group_edit_permissions(context: Context, data_dict: DataDict) -> AuthResult:
    user = context['user']
    group = logic_auth.get_group_object(context, data_dict)

    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')

    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to'
                     ' edit permissions of group %s') %
            (str(user), group.id)}
    else:
        return {'success': True}
