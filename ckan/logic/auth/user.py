from __future__ import annotations



from .create import _check_follow_auth

from .delete import _check_unfollow_auth

from .get import _followee_list

from .group import group_member_create

from ckan import model

from ckan.common import _, config

from ckan.logic.auth import restrict_anon

from ckan.types import AuthResult, Context, DataDict

from typing import Optional

import ckan.authz as authz

import ckan.logic as logic

import ckan.logic.auth as logic_auth





def user_list(context: Context, data_dict: DataDict) -> AuthResult:
    # Users list is visible by default
    if data_dict.get('email'):
        # only sysadmins can specify the 'email' parameter
        return {'success': False}
    if not config.get('ckan.auth.public_user_details'):
        return restrict_anon(context)
    else:
        return {'success': True}

def user_show(context: Context, data_dict: DataDict) -> AuthResult:
    # By default, user details can be read by anyone, but some properties like
    # the API key are stripped at the action level if not not logged in.
    if not config.get('ckan.auth.public_user_details'):
        return restrict_anon(context)
    else:
        return {'success': True}

def user_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('user_list', context, data_dict)

def get_site_user(context: Context, data_dict: DataDict) -> AuthResult:
    # FIXME this is available to sysadmins currently till
    # @auth_sysadmins_check decorator is added
    return {'success': False,
            'msg': 'Only internal services allowed to use this action'}

def user_follower_list(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('sysadmin', context, data_dict)

def dataset_follower_list(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('sysadmin', context, data_dict)

def group_follower_list(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('sysadmin', context, data_dict)

def organization_follower_list(context: Context,
                               data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('sysadmin', context, data_dict)

def followee_list(context: Context, data_dict: DataDict) -> AuthResult:
    return _followee_list(context, data_dict)

@logic.auth_audit_exempt
def user_followee_list(context: Context, data_dict: DataDict) -> AuthResult:
    return _followee_list(context, data_dict)

@logic.auth_audit_exempt
def dataset_followee_list(context: Context, data_dict: DataDict) -> AuthResult:
    return _followee_list(context, data_dict)

@logic.auth_audit_exempt
def group_followee_list(context: Context, data_dict: DataDict) -> AuthResult:
    return _followee_list(context, data_dict)

@logic.auth_audit_exempt
def organization_followee_list(context: Context,
                               data_dict: DataDict) -> AuthResult:
    return _followee_list(context, data_dict)

def api_token_list(context: Context, data_dict: DataDict) -> AuthResult:
    """List all available tokens for current user.
    """
    # Support "user" for backwards compatibility
    id_or_name = data_dict.get("user_id", data_dict.get("user"))
    user = model.User.get(id_or_name)
    success = user is not None and user.name == context[u'user']

    return {u'success': success}

def dataset_followee_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of datasets followed by a user are visible.
    Visible to all by default.'''
    return {'success': True}

def group_followee_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of groups followed by a user are visible.
    Visible to all by default.'''
    return {'success': True}

def organization_followee_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of organizations followed by a user are visible.
    Visible to all by default.'''
    return {'success': True}

def user_followee_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of users followed by a user are visible.
    Visible to all by default.'''
    return {'success': True}

def followee_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of objects (of any type) followed by a user are visible.
    Visible to all by default.'''
    return {'success': True}

def dataset_follower_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of followers of a dataset are visible.
    Visible to all by default.'''
    return {'success': True}

def group_follower_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of followers of a group are visible.
    Visible to all by default.'''
    return {'success': True}

def organization_follower_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of followers of an organization are visible.
    Visible to all by default.'''
    return {'success': True}

def user_follower_count(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the number of followers of a user are visible.
    Visible to all by default.'''
    return {'success': True}

def am_following_dataset(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the information about following a dataset is visible.
    Visible to all by default.'''
    return {'success': True}

def am_following_group(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the information about following a group is visible.
    Visible to all by default.'''
    return {'success': True}

def am_following_user(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the information about following a user is visible.
    Visible to all by default.'''
    return {'success': True}

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

def api_token_create(context: Context, data_dict: DataDict) -> AuthResult:
    """Create new token for current user.
    """
    user = model.User.get(data_dict['user'])
    assert user
    return {'success': user.name == context['user']}

def follow_group(context: Context,
                 data_dict: DataDict) -> AuthResult:
    """
    Only logged in users who can read a group can follow it.
    """
    if not _check_follow_auth(context):
        return {'success': False,
                'msg': _("You must be logged in to follow groups")}

    return authz.is_authorized('group_show', context, data_dict)

def follow_dataset(context: Context,
                   data_dict: DataDict) -> AuthResult:
    """
    Only logged in users who can read a dataset can follow it.
    """
    if not _check_follow_auth(context):
        return {'success': False,
                'msg': _("You must be logged in to follow datasets")}

    return authz.is_authorized('package_show', context, data_dict)

def follow_user(context: Context,
                data_dict: DataDict) -> AuthResult:
    """
    Only logged in users can follow a user.
    """
    if not _check_follow_auth(context):
        return {'success': False,
                'msg': _("You must be logged in to follow users")}

    return authz.is_authorized('user_show', context, data_dict)

@logic.auth_allow_anonymous_access
def user_update(context: Context, data_dict: DataDict) -> AuthResult:
    user = context['user']

    # FIXME: We shouldn't have to do a try ... except here, validation should
    # have ensured that the data_dict contains a valid user id before we get to
    # authorization.
    try:
        user_obj = logic_auth.get_user_object(context, data_dict)
    except logic.NotFound:
        return {'success': False, 'msg': _('User not found')}

    # If the user has a valid reset_key in the db, and that same reset key
    # has been posted in the data_dict, we allow the user to update
    # her account without using her password or API key.
    if user_obj.reset_key and 'reset_key' in data_dict:
        if user_obj.reset_key == data_dict['reset_key']:
            return {'success': True}

    if not user:
        return {'success': False,
                'msg': _('Have to be logged in to edit user')}

    if user == user_obj.name:
        # Allow users to update their own user accounts.
        return {'success': True}
    else:
        # Don't allow users to update other users' accounts.
        return {'success': False,
                'msg': _('User %s not authorized to edit user %s') %
                        (user, user_obj.id)}

def user_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}

def api_token_revoke(context: Context, data_dict: DataDict) -> AuthResult:
    """Delete token.
    """
    if authz.auth_is_anon_user(context):
        return {u'success': False}

    token = model.ApiToken.get(data_dict[u'jti'])
    # Do not make distinction between absent keys and keys not owned
    # by user in order to prevent accidental key discovery.
    if token is None or token.owner and token.owner.name != context[u'user']:
        return {u'success': False}
    return {u'success': True}

def unfollow_group(context: Context,
                   data_dict: DataDict) -> AuthResult:
    """
    Only logged in users can unfollow a group.
    """
    if _check_unfollow_auth(context):
        return {'success': True}
    return {'success': False,
            'msg': _("You must be logged in to unfollow groups")}

def unfollow_dataset(context: Context,
                     data_dict: DataDict) -> AuthResult:
    """
    Only logged in users can unfollow a dataset.
    """
    if _check_unfollow_auth(context):
        return {'success': True}
    return {'success': False,
            'msg': _("You must be logged in to unfollow datasets")}

def unfollow_user(context: Context,
                  data_dict: DataDict) -> AuthResult:
    """
    Only logged in users can unfollow a dataset.
    """
    if _check_unfollow_auth(context):
        return {'success': True}
    return {'success': False,
            'msg': _("You must be logged in to unfollow users")}

def user_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('user_update', context, data_dict)
