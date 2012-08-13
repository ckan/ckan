from ckan.logic.auth import (get_package_object, get_group_object,
    get_user_object, get_resource_object, get_related_object)
from ckan.logic.auth.publisher import _groups_intersect
import ckan.logic as logic
from ckan.authz import Authorizer
from ckan.lib.base import _

# FIXME: Which is worse, 'from module import foo' or duplicating these
# functions in this module?
from ckan.logic.auth.create import vocabulary_create, tag_create

def package_create(context, data_dict=None):
    model = context['model']
    user = context['user']
    userobj = model.User.get(user)

    if userobj and len(userobj.get_groups()):
        return {'success': True}

    return {'success': False,
            'msg': _('You must be logged in and be within a group to create '
                     'a package')}


def related_create(context, data_dict=None):
    model = context['model']
    user = context['user']
    userobj = model.User.get(user)

    if not userobj:
        return {'success': False, 'msg': _('You must be logged in to add a related item')}

    if 'dataset_id' in data_dict:
        # If this is to be associated with a dataset then we need to make sure that
        # the user doing so is a member of that group
        dataset = model.Package.get(data_dict['dataset_id'])
        if dataset and not _groups_intersect( userobj.get_groups(),
                                              dataset.get_groups() ):
            return {'success': False,
                    'msg': _('You do not have permission to create an item')}

    return {'success': True }



def resource_create(context, data_dict):
    # resource_create runs through package_update, no need to
    # check users eligibility to add resource to package here
    model = context['model']
    user = context['user']
    userobj = model.User.get(user)

    if userobj:
        return {'success': True}
    return {'success': False,
            'msg': _('You must be logged in to create a resource')}

def package_relationship_create(context, data_dict):
    """
    Permission for users to create a new package relationship requires that the
    user share a group with both packages.
    """
    model = context['model']
    user = context['user']

    id = data_dict.get('id', '')
    id2 = data_dict.get('id2', '')

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)

    if not pkg1 or not pkg2:
        return {'success': False, 'msg': _('Two package IDs are required')}

    pkg1grps = pkg1.get_groups('organization')
    pkg2grps = pkg2.get_groups('organization')

    usergrps = model.User.get( user ).get_groups('organization')
    authorized = _groups_intersect( usergrps, pkg1grps ) and _groups_intersect( usergrps, pkg2grps )
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit these packages') % str(user)}
    else:
        return {'success': True}

def group_create(context, data_dict=None):
    """
    Group create permission.  If a group is provided, within which we want to create a group
    then we check that the user is within that group.  If not then we just say Yes for now
    although there may be some approval issues elsewhere.
    """
    model = context['model']
    user  = context['user']

    if not model.User.get(user):
        return {'success': False, 'msg': _('User is not authorized to create groups') }

    if Authorizer.is_sysadmin(user):
        return {'success': True}

    try:
        # If the user is doing this within another group then we need to make sure that
        # the user has permissions for this group.
        group = get_group_object( context )
    except logic.NotFound:
        return { 'success' : True }

    userobj = model.User.get( user )
    if not userobj:
        return {'success': False, 'msg': _('User %s not authorized to create groups') % str(user)}

    authorized = _groups_intersect( userobj.get_groups('organization'), [group] )
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

def activity_create(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}
