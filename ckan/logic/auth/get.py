# encoding: utf-8

import ckan.logic as logic
import ckan.authz as authz
from ckan.lib.base import _
from ckan.logic.auth import (get_package_object, get_group_object,
                            get_resource_object)
from ckan.lib.plugins import get_permission_labels


def sysadmin(context, data_dict):
    ''' This is a pseudo check if we are a sysadmin all checks are true '''
    return {'success': False, 'msg': _('Not authorized')}


def site_read(context, data_dict):
    """\
    This function should be deprecated. It is only here because we couldn't
    get hold of Friedrich to ask what it was for.

    ./ckan/controllers/api.py
    """

    # FIXME we need to remove this for now we allow site read
    return {'success': True}

def package_search(context, data_dict):
    # Everyone can search by default
    return {'success': True}

def package_list(context, data_dict):
    # List of all active packages are visible by default
    return {'success': True}


def current_package_list_with_resources(context, data_dict):
    return authz.is_authorized('package_list', context, data_dict)


def revision_list(context, data_dict):
    # In our new model everyone can read the revison list
    return {'success': True}


def group_revision_list(context, data_dict):
    return authz.is_authorized('group_show', context, data_dict)


def organization_revision_list(context, data_dict):
    return authz.is_authorized('group_show', context, data_dict)


def package_revision_list(context, data_dict):
    return authz.is_authorized('package_show', context, data_dict)


def group_list(context, data_dict):
    # List of all active groups is visible by default
    return {'success': True}


def group_list_authz(context, data_dict):
    return authz.is_authorized('group_list', context, data_dict)


def group_list_available(context, data_dict):
    return authz.is_authorized('group_list', context, data_dict)


def organization_list(context, data_dict):
    # List of all active organizations are visible by default
    return {'success': True}

def organization_list_for_user(context, data_dict):
    return {'success': True}

def license_list(context, data_dict):
    # Licenses list is visible by default
    return {'success': True}

def vocabulary_list(context, data_dict):
    # List of all vocabularies are visible by default
    return {'success': True}

def tag_list(context, data_dict):
    # Tags list is visible by default
    return {'success': True}

def user_list(context, data_dict):
    # Users list is visible by default
    return {'success': True}

def package_relationships_list(context, data_dict):
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

def package_show(context, data_dict):
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


def resource_show(context, data_dict):
    model = context['model']
    user = context.get('user')
    resource = get_resource_object(context, data_dict)

    # check authentication against package
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(_('No package found for this resource, cannot check auth.'))

    pkg_dict = {'id': pkg.id}
    authorized = authz.is_authorized('package_show', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to read resource %s') % (user, resource.id)}
    else:
        return {'success': True}


def resource_view_show(context, data_dict):
    return authz.is_authorized('resource_show', context, data_dict)


def resource_view_list(context, data_dict):
    return authz.is_authorized('resource_show', context, data_dict)


def revision_show(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def group_show(context, data_dict):
    user = context.get('user')
    group = get_group_object(context, data_dict)
    if group.state == 'active':
        return {'success': True}
    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'read')
    if authorized:
        return {'success': True}
    else:
        return {'success': False, 'msg': _('User %s not authorized to read group %s') % (user, group.id)}


def organization_show(context, data_dict):
    return authz.is_authorized('group_show', context, data_dict)


def vocabulary_show(context, data_dict):
    # Allow viewing of vocabs by default
    return {'success': True}

def tag_show(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def user_show(context, data_dict):
    # By default, user details can be read by anyone, but some properties like
    # the API key are stripped at the action level if not not logged in.
    return {'success': True}


def package_autocomplete(context, data_dict):
    return authz.is_authorized('package_list', context, data_dict)


def group_autocomplete(context, data_dict):
    return authz.is_authorized('group_list', context, data_dict)


def organization_autocomplete(context, data_dict):
    return authz.is_authorized('organization_list', context, data_dict)


def tag_autocomplete(context, data_dict):
    return authz.is_authorized('tag_list', context, data_dict)


def user_autocomplete(context, data_dict):
    return authz.is_authorized('user_list', context, data_dict)


def format_autocomplete(context, data_dict):
    return {'success': True}

def task_status_show(context, data_dict):
    return {'success': True}

def resource_status_show(context, data_dict):
    return {'success': True}


## Modifications for rest api
def package_show_rest(context, data_dict):
    return authz.is_authorized('package_show', context, data_dict)


def group_show_rest(context, data_dict):
    return authz.is_authorized('group_show', context, data_dict)


def tag_show_rest(context, data_dict):
    return authz.is_authorized('tag_show', context, data_dict)


def get_site_user(context, data_dict):
    # FIXME this is available to sysadmins currently till
    # @auth_sysadmins_check decorator is added
    return {'success': False,
            'msg': 'Only internal services allowed to use this action'}


def member_roles_list(context, data_dict):
    return {'success': True}


def dashboard_activity_list(context, data_dict):
    # FIXME: context['user'] could be an IP address but that case is not
    # handled here. Maybe add an auth helper function like is_logged_in().
    if context.get('user'):
        return {'success': True}
    else:
        return {'success': False,
                'msg': _("You must be logged in to access your dashboard.")}


def dashboard_new_activities_count(context, data_dict):
    # FIXME: This should go through check_access() not call is_authorized()
    # directly, but wait until 2939-orgs is merged before fixing this.
    # This is so a better not authourized message can be sent.
    return authz.is_authorized('dashboard_activity_list',
            context, data_dict)


def user_follower_list(context, data_dict):
    return authz.is_authorized('sysadmin', context, data_dict)


def dataset_follower_list(context, data_dict):
    return authz.is_authorized('sysadmin', context, data_dict)


def group_follower_list(context, data_dict):
    return authz.is_authorized('sysadmin', context, data_dict)


def organization_follower_list(context, data_dict):
    return authz.is_authorized('sysadmin', context, data_dict)


def _followee_list(context, data_dict):
    model = context['model']

    # Visitors cannot see what users are following.
    authorized_user = model.User.get(context.get('user'))
    if not authorized_user:
        return {'success': False, 'msg': _('Not authorized')}

    # Any user is authorized to see what she herself is following.
    requested_user = model.User.get(data_dict.get('id'))
    if authorized_user == requested_user:
        return {'success': True}

    # Sysadmins are authorized to see what anyone is following.
    return authz.is_authorized('sysadmin', context, data_dict)


def followee_list(context, data_dict):
    return _followee_list(context, data_dict)


@logic.auth_audit_exempt
def user_followee_list(context, data_dict):
    return _followee_list(context, data_dict)


@logic.auth_audit_exempt
def dataset_followee_list(context, data_dict):
    return _followee_list(context, data_dict)


@logic.auth_audit_exempt
def group_followee_list(context, data_dict):
    return _followee_list(context, data_dict)


@logic.auth_audit_exempt
def organization_followee_list(context, data_dict):
    return _followee_list(context, data_dict)


def user_reset(context, data_dict):
    return {'success': True}


def request_reset(context, data_dict):
    return {'success': True}


def help_show(context, data_dict):
    return {'success': True}


def config_option_show(context, data_dict):
    '''Show runtime-editable configuration option. Only sysadmins.'''
    return {'success': False}


def config_option_list(context, data_dict):
    '''List runtime-editable configuration options. Only sysadmins.'''
    return {'success': False}


def job_list(context, data_dict):
    '''List background jobs. Only sysadmins.'''
    return {'success': False}


def job_show(context, data_dict):
    '''Show background job. Only sysadmins.'''
    return {'success': False}
