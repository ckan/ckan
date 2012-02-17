from ckan.logic.auth import get_package_object, get_group_object, \
    get_user_object, get_resource_object
from ckan.lib.base import _
from ckan.logic.auth.publisher import _groups_intersect
from ckan.authz import Authorizer
from ckan.logic.auth import get_package_object, get_group_object, get_resource_object


def site_read(context, data_dict):
    """\
    This function should be deprecated. It is only here because we couldn't
    get hold of Friedrich to ask what it was for.

    ./ckan/controllers/api.py
    """
    return {'success': True}

def package_search(context, data_dict):
    # Everyone can search by default
    return {'success': True}

def package_list(context, data_dict):
    # List of all active packages are visible by default
    return {'success': True}

def current_package_list_with_resources(context, data_dict):
    return package_list(context, data_dict)

def revision_list(context, data_dict):
    # In our new model everyone can read the revison list
    return {'success': True}

def group_revision_list(context, data_dict):
    return group_show(context, data_dict)

def package_revision_list(context, data_dict):
    return package_show(context, data_dict)

def group_list(context, data_dict):
    # List of all active groups is visible by default
    return {'success': True}

def group_list_authz(context, data_dict):
    return group_list(context, data_dict)

def group_list_available(context, data_dict):
    return group_list(context, data_dict)

def licence_list(context, data_dict):
    # Licences list is visible by default
    return {'success': True}

def tag_list(context, data_dict):
    # Tags list is visible by default
    return {'success': True}

def user_list(context, data_dict):
    # Users list is visible by default
    return {'success': True}

def package_relationships_list(context, data_dict):
    return {'success': True}

def package_show(context, data_dict):
    """ Package show permission checks the user group if the state is deleted """
    model = context['model']
    package = get_package_object(context, data_dict)
        
    if package.state == 'deleted':
        if 'ignore_auth' in context and context['ignore_auth']:
            return {'success': True}            
            
        user = context.get('user')

        if not user:
            return {'success': False, 'msg': _('User not authorized to read package %s') % (package.id)}

        userobj = model.User.get( user )
        if not userobj:
            return {'success': False, 'msg': _('User %s not authorized to read package %s') % (str(user),package.id)}

        if not _groups_intersect( userobj.get_groups('publisher'), package.get_groups('publisher') ):
            return {'success': False, 'msg': _('User %s not authorized to read package %s') % (str(user),package.id)}
    
    return {'success': True}

def resource_show(context, data_dict):
    """ Resource show permission checks the user group if the package state is deleted """    
    model = context['model']
    user = context.get('user')
    resource = get_resource_object(context, data_dict)
    package = resource.revision_group.package

    if package.state == 'deleted':
        userobj = model.User.get( user )
        if not userobj:
            return {'success': False, 'msg': _('User %s not authorized to read resource %s') % (str(user),package.id)}    
        if not _groups_intersect( userobj.get_groups('publisher'), package.get_groups('publisher') ):
            return {'success': False, 'msg': _('User %s not authorized to read package %s') % (str(user),package.id)}
    
    pkg_dict = {'id': pkg.id}
    return package_show(context, pkg_dict)


def revision_show(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def group_show(context, data_dict):
    """ Group show permission checks the user group if the state is deleted """
    model = context['model']
    user = context.get('user')
    group = get_group_object(context, data_dict)
    userobj = model.User.get( user )
            
    if group.state == 'deleted':
        if not user or \
           not _groups_intersect( userobj.get_groups('publisher'), group.get_groups('publisher') ):
            return {'success': False, 'msg': _('User %s not authorized to show group %s') % (str(user),group.id)}    
    
    return {'success': True}

def tag_show(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def user_show(context, data_dict):
    # By default, user details can be read by anyone, but some properties like
    # the API key are stripped at the action level if not not logged in.
    return {'success': True}

def package_autocomplete(context, data_dict):
    return package_list(context, data_dict)

def group_autocomplete(context, data_dict):
    return group_list(context, data_dict)

def tag_autocomplete(context, data_dict):
    return tag_list(context, data_dict)

def user_autocomplete(context, data_dict):
    return user_list(context, data_dict)

def format_autocomplete(context, data_dict):
    return {'success': True}

def task_status_show(context, data_dict):
    return {'success': True}

## Modifications for rest api

def package_show_rest(context, data_dict):
    return package_show(context, data_dict)

def group_show_rest(context, data_dict):
    return group_show(context, data_dict)

def tag_show_rest(context, data_dict):
    return tag_show(context, data_dict)

def get_site_user(context, data_dict):
    if not context.get('ignore_auth'):
        return {'success': False, 'msg': 'Only internal services allowed to use this action'}
    else:
        return {'success': True}
