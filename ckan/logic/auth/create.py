# encoding: utf-8

from typing import Optional

import ckan.logic as logic
import ckan.authz as authz
import ckan.logic.auth as logic_auth

from ckan import model
from ckan.common import _
from ckan.types import Context, DataDict, AuthResult


def file_upload(context: Context,
                data_dict: Optional[DataDict] = None) -> AuthResult:
    user = context['user']
    if authz.auth_is_anon_user(context):
        return {'success': False, 'msg': _(
            'User %s not authorized to create packages') % user}
    return {'success': True}


def _check_group_auth(context: Context, data_dict: Optional[DataDict]) -> bool:
    '''Has this user got update permission for all of the given groups?
    If there is a package in the context then ignore that package's groups.
    (owner_org is checked elsewhere.)
    :returns: False if not allowed to update one (or more) of the given groups.
              True otherwise. i.e. True is the default. A blank data_dict
              mentions no groups, so it returns True.

    '''
    # FIXME This code is shared among other logic.auth files and should be
    # somewhere better
    if not data_dict:
        return True

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


def _check_follow_auth(context: Context) -> bool:
    if not context.get('user'):
        return False

    userobj = model.User.get(context['user'])
    if not userobj:
        return False

    return True
