from ckan.logic.auth import get_package_object, get_group_object, get_authorization_group_object, \
    get_user_object, get_resource_object
from ckan.logic.auth.publisher import _groups_intersect    
from ckan.logic import check_access_old, NotFound
from ckan.authz import Authorizer
from ckan.lib.base import _


def package_create(context, data_dict=None):
    model = context['model']
    user = context['user']

    # We need the publisher group passed in as part of this request
    try:
        group = get_group_object( context )
    except NotFound:
        return {'success': False, 
                'msg': _('User %s not authorized to create a package without a group specified') % str(user)}        
    
    userobj = model.User.get( user )
    if not _groups_intersect( userobj.get_groups('publisher'), group.get_groups('publisher') ):
        return {'success': False, 'msg': _('User %s not authorized to create a package here') % str(user)}    

    return {'success': True}

def resource_create(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def package_relationship_create(context, data_dict):
    model = context['model']
    user = context['user']

    id = data_dict['id']
    id2 = data_dict['id2']
    pkg1grps = model.Package.get(id).get_groups('publisher')
    pkg2grps = model.Package.get(id2).get_groups('publisher')

    usergrps = model.User.get( user ).get_groups('publisher')
    authorized = _groups_intersect( usergrps, pkg1grps ) and _groups_intersect( usergrps, pkg2grps )    
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit these packages') % str(user)}
    else:
        return {'success': True}

def group_create(context, data_dict=None):
    model = context['model']
    user = context['user']
   
    # TODO: We need to check whether this group is being created within another group
    try:
        group = get_group_object( context )
    except NotFound:
        return { 'success' : True }
        
    usergrps = User.get( user ).get_groups('publisher')
    authorized = _groups_intersect( usergrps, group.get_groups('publisher') )
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to create groups') % str(user)}
    else:
        return {'success': True}

def authorization_group_create(context, data_dict=None):
    return {'success': False, 'msg': _('Authorization groups not implemented in this profile') % str(user)}


def rating_create(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def user_create(context, data_dict=None):
    return {'success': True}


def check_group_auth(context, data_dict):
    # Maintained for function count in profiles, until we can rename to _*
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
