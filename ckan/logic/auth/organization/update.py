import ckan.logic as logic
from ckan.logic.auth import (get_package_object, get_group_object,
                             get_user_object, get_resource_object,
                             get_organization_object, get_related_object)
from ckan.logic.auth.organization import _groups_intersect
from ckan.logic.auth.organization.create import package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _


def make_latest_pending_package_active(context, data_dict):
    return package_update(context, data_dict)

def package_update(context, data_dict):
    model = context['model']
    user = context.get('user')
    package = get_package_object(context, data_dict)

    if Authorizer().is_sysadmin(unicode(user)):
        return { 'success': True }

    userobj = model.User.get( user )
    if not userobj or \
       not _groups_intersect( userobj.get_groups('organization'), package.get_groups('organization') ):
        return {'success': False,
                'msg': _('User %s not authorized to edit packages in these groups') % str(user)}

    return {'success': True}

def resource_update(context, data_dict):
    """
    Update resource permission checks the user is in a group that the resource's
    package is also a member of.
    """
    model = context['model']
    user = context.get('user')
    resource = get_resource_object(context, data_dict)
    userobj = model.User.get( user )

    if Authorizer().is_sysadmin(unicode(user)):
        return { 'success': True }

    if not userobj:
        return {'success': False, 'msg': _('User %s not authorized to edit resources in this package') % str(user)}

    if not _groups_intersect( userobj.get_groups('organization'), resource.resource_group.package.get_groups('organization') ):
        return {'success': False, 'msg': _('User %s not authorized to edit resources in this package') % str(user)}

    return {'success': True}

def package_relationship_update(context, data_dict):
    return package_relationship_create(context, data_dict)

def package_change_state(context, data_dict):
    return package_update( context, data_dict )

def package_edit_permissions(context, data_dict):
    return {'success': False,
            'msg': _('Package edit permissions is not available')}

def organization_add_dataset(context, data_dict):
    """
    Can the user add a dataset to the organization
    """
    model = context['model']
    user = context.get('user','')
    group = get_group_object(context, data_dict)

    if Authorizer().is_sysadmin(unicode(user)):
        return { 'success': True }

    userobj = model.User.get( user )
    if not userobj:
        return { 'success' : False, 'msg': _('Could not find user %s') % str(user) }

    # Any member of this group can add a package to it.
    if not _groups_intersect(userobj.get_groups( 'organization' ), [group]):
        return { 'success': False, 'msg': _('User %s not authorized to add datasets to this organization') % str(user) }

    return { 'success': True }


def group_update(context, data_dict):
    """
    Group edit permission.  Checks that a valid user is supplied and that the user is
    a member of the group currently with any capacity.
    """
    model = context['model']
    user = context.get('user','')
    group = get_group_object(context, data_dict)

    if not user:
        return {'success': False, 'msg': _('Only members of this group are authorized to edit this group')}

    # Sys admins should be allowed to update groups
    if Authorizer().is_sysadmin(unicode(user)):
        return { 'success': True }

    # Only allow package update if the user and package groups intersect
    userobj = model.User.get( user )
    if not userobj:
        return { 'success' : False, 'msg': _('Could not find user %s') % str(user) }

    # Only admins of this group should be able to update this group
    if not _groups_intersect( userobj.get_groups(None, 'admin' ), [group] ):
        return { 'success': False, 'msg': _('User %s not authorized to edit this group') % str(user) }

    return { 'success': True }

def organization_update(context, data_dict):
    """
    Organization edit permission.  Checks that a valid user is supplied and that the user is
    a member of the group currently with admin capacity.
    """
    model = context['model']
    user = context.get('user','')
    organization = get_organization_object(context, data_dict)

    if not user:
        return {'success': False, 'msg': _('Only members of this organization are authorized to edit this group')}

    # Sys admins should be allowed to update groups
    if Authorizer().is_sysadmin(unicode(user)):
        return { 'success': True }

    # Only allow package update if the user and package groups intersect
    userobj = model.User.get( user )
    if not userobj:
        return { 'success' : False, 'msg': _('Could not find user %s') % str(user) }

    # Only admins of this group should be able to update this group
    if not _groups_intersect( userobj.get_groups( 'organization', 'admin' ), [organization] ):
        return { 'success': False, 'msg': _('User %s not authorized to edit this organization') % str(user) }

    return { 'success': True }


def related_update(context, data_dict):
    model = context['model']
    user = context['user']
    if not user:
        return {'success': False, 'msg': _('Only the owner can update a related item')}

    related = get_related_object(context, data_dict)
    userobj = model.User.get( user )
    if not userobj or userobj.id != related.owner_id:
        return {'success': False, 'msg': _('Only the owner can update a related item')}

    return {'success': True}

def group_change_state(context, data_dict):
    return group_update(context, data_dict)

def organization_change_state(context, data_dict):
    return organization_update(context, data_dict)

def group_edit_permissions(context, data_dict):
    return {'success': False, 'msg': _('Group edit permissions is not implemented')}

def organization_edit_permissions(context, data_dict):
    return {'success': False, 'msg': _('Organization edit permissions is not implemented')}

def user_update(context, data_dict):
    model = context['model']
    user = context['user']
    user_obj = get_user_object(context, data_dict)

    if not (Authorizer().is_sysadmin(unicode(user)) or user == user_obj.name) and \
       not ('reset_key' in data_dict and data_dict['reset_key'] == user_obj.reset_key):
        return {'success': False, 'msg': _('User %s not authorized to edit user %s') % (str(user), user_obj.id)}

    return {'success': True}

def revision_change_state(context, data_dict):
    model = context['model']
    user = context['user']

    authorized = Authorizer().is_sysadmin(unicode(user))
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to change state of revision' ) % str(user)}
    else:
        return {'success': True}

def task_status_update(context, data_dict):
    model = context['model']
    user = context['user']

    if 'ignore_auth' in context and context['ignore_auth']:
        return {'success': True}

    authorized =  Authorizer().is_sysadmin(unicode(user))
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to update task_status table') % str(user)}
    else:
        return {'success': True}

def term_translation_update(context, data_dict):

    model = context['model']
    user = context['user']

    if 'ignore_auth' in context and context['ignore_auth']:
        return {'success': True}

    authorized =  Authorizer().is_sysadmin(unicode(user))
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to update term_translation table') % str(user)}
    else:
        return {'success': True}



## Modifications for rest api

def package_update_rest(context, data_dict):
    model = context['model']
    user = context['user']

    if user in (model.PSEUDO_USER__VISITOR, ''):
        return {'success': False, 'msg': _('Valid API key needed to edit a package')}

    return package_update(context, data_dict)

def group_update_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if user in (model.PSEUDO_USER__VISITOR, ''):
        return {'success': False, 'msg': _('Valid API key needed to edit a group')}

    return group_update(context, data_dict)

def organization_update_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if user in (model.PSEUDO_USER__VISITOR, ''):
        return {'success': False, 'msg': _('Valid API key needed to edit a group')}

    return organization_update(context, data_dict)


def vocabulary_update(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}

