# encoding: utf-8

import ckan.logic as logic
import ckan.authz as authz
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


def site_read(context: Context, data_dict: DataDict) -> AuthResult:
    """\
    This function should be deprecated. It is only here because we couldn't
    get hold of Friedrich to ask what it was for.

    ./ckan/controllers/api.py
    """

    # FIXME we need to remove this for now we allow site read
    return {'success': True}


def package_search(context: Context, data_dict: DataDict) -> AuthResult:
    # Everyone can search by default
    return {'success': True}


def package_list(context: Context, data_dict: DataDict) -> AuthResult:
    # List of all active packages are visible by default
    return {'success': True}


def current_package_list_with_resources(context: Context,
                                        data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_list', context, data_dict)


def group_list(context: Context, data_dict: DataDict) -> AuthResult:
    # List of all active groups is visible by default
    return {'success': True}


def group_list_authz(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('group_list', context, data_dict)


def group_list_available(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('group_list', context, data_dict)


def organization_list(context: Context, data_dict: DataDict) -> AuthResult:
    # List of all active organizations are visible by default
    return {'success': True}


def organization_list_for_user(context: Context,
                               data_dict: DataDict) -> AuthResult:
    return {'success': True}


def license_list(context: Context, data_dict: DataDict) -> AuthResult:
    # Licenses list is visible by default
    return {'success': True}


def vocabulary_list(context: Context, data_dict: DataDict) -> AuthResult:
    # List of all vocabularies are visible by default
    return {'success': True}


def tag_list(context: Context, data_dict: DataDict) -> AuthResult:
    # Tags list is visible by default
    return {'success': True}


def user_list(context: Context, data_dict: DataDict) -> AuthResult:
    # Users list is visible by default
    if data_dict.get('email'):
        # only sysadmins can specify the 'email' parameter
        return {'success': False}
    if not config.get('ckan.auth.public_user_details'):
        return restrict_anon(context)
    else:
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


def resource_show(context: Context, data_dict: DataDict) -> AuthResult:
    model = context['model']
    user = context.get('user')
    resource = get_resource_object(context, data_dict)

    # check authentication against package
    assert resource.package_id
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(_('No package found for this resource, cannot check auth.'))

    pkg_dict = {'id': pkg.id}
    authorized = authz.is_authorized('package_show', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to read resource %s') % (user, resource.id)}
    else:
        return {'success': True}


def resource_view_show(context: Context, data_dict: DataDict) -> AuthResult:

    model = context['model']

    resource_view = model.ResourceView.get(data_dict['id'])
    if not resource_view:
        raise logic.NotFound(_('Resource view not found, cannot check auth.'))
    resource = model.Resource.get(resource_view.resource_id)

    assert resource
    return authz.is_authorized('resource_show', context, {'id': resource.id})


def resource_view_list(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('resource_show', context, data_dict)


def group_show(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get('user')
    group = get_group_object(context, data_dict)
    if group.state == 'active':
        if config.get('ckan.auth.public_user_details') or \
            (not asbool(data_dict.get('include_users', False)) and
                (data_dict.get('object_type', None) != 'user')):
            return {'success': True}
    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'read')
    if authorized:
        return {'success': True}
    else:
        return {'success': False, 'msg': _('User %s not authorized to read group %s') % (user, group.id)}


def organization_show(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('group_show', context, data_dict)


def vocabulary_show(context: Context, data_dict: DataDict) -> AuthResult:
    # Allow viewing of vocabs by default
    return {'success': True}


def tag_show(context: Context, data_dict: DataDict) -> AuthResult:
    # No authz check in the logic function
    return {'success': True}


def user_show(context: Context, data_dict: DataDict) -> AuthResult:
    # By default, user details can be read by anyone, but some properties like
    # the API key are stripped at the action level if not not logged in.
    if not config.get('ckan.auth.public_user_details'):
        return restrict_anon(context)
    else:
        return {'success': True}


def package_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_list', context, data_dict)


def group_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('group_list', context, data_dict)


def organization_autocomplete(context: Context,
                              data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('organization_list', context, data_dict)


def tag_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('tag_list', context, data_dict)


def user_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('user_list', context, data_dict)


def format_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}


def task_status_show(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}


def get_site_user(context: Context, data_dict: DataDict) -> AuthResult:
    # FIXME this is available to sysadmins currently till
    # @auth_sysadmins_check decorator is added
    return {'success': False,
            'msg': 'Only internal services allowed to use this action'}


def member_roles_list(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}

def user_follower_list(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('sysadmin', context, data_dict)


def dataset_follower_list(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('sysadmin', context, data_dict)


def group_follower_list(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('sysadmin', context, data_dict)


def organization_follower_list(context: Context,
                               data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('sysadmin', context, data_dict)


def _followee_list(context: Context, data_dict: DataDict) -> AuthResult:
    model = context['model']

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


def user_reset(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}


def request_reset(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}


def help_show(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}


def config_option_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Show runtime-editable configuration option. Only sysadmins.'''
    return {'success': False}


def config_option_list(context: Context, data_dict: DataDict) -> AuthResult:
    '''List runtime-editable configuration options. Only sysadmins.'''
    return {'success': False}


def job_list(context: Context, data_dict: DataDict) -> AuthResult:
    '''List background jobs. Only sysadmins.'''
    return {'success': False}


def job_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Show background job. Only sysadmins.'''
    return {'success': False}


def api_token_list(context: Context, data_dict: DataDict) -> AuthResult:
    """List all available tokens for current user.
    """
    # Support "user" for backwards compatibility
    id_or_name = data_dict.get("user_id", data_dict.get("user"))
    user = context[u'model'].User.get(id_or_name)
    success = user is not None and user.name == context[u'user']

    return {u'success': success}


def package_collaborator_list(context: Context,
                              data_dict: DataDict) -> AuthResult:
    '''Checks if a user is allowed to list the collaborators from a dataset

    See :py:func:`~ckan.authz.can_manage_collaborators` for details
    '''
    user = context['user']
    model = context['model']

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


def status_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Show information about the site's configuration. Visible to all by default.'''
    return {'success': True}


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

def group_package_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the set of datasets belonging to a group is visible.
    Visible to all by default.'''
    return {'success': True}

def member_list(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the members of a given group are visible.
    Visible to all by default.'''
    return {'success': True}

def resource_search(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if resource search is allowed.
    Allowed for all by default.'''
    return {'success': True}

def tag_search(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if tag search is allowed.
    Allowed for all by default.'''
    return {'success': True}

def term_translation_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the translations for the given term(s) and language(s) are visible.
    Visible to all by default.'''
    return {'success': True}
