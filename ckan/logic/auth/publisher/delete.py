from ckan.logic.auth import get_package_object, get_group_object, get_authorization_group_object, \
    get_user_object, get_resource_object
from ckan.logic.auth import get_package_object, get_group_object
from ckan.logic.auth.publisher import _groups_intersect
from ckan.logic.auth.publisher.create import package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _

def package_delete(context, data_dict):
    model = context['model']
    user = context['user']
    package = get_package_object(context, data_dict)
    userobj = model.User.get( user )

    if not userobj or \
       not _groups_intersect( userobj.get_groups('publisher'), package.get_groups('publisher') ):
        return {'success': False, 
                'msg': _('User %s not authorized to delete packages in these group') % str(user)}
    return {'success': True}
    
def package_relationship_delete(context, data_dict):
    return package_relationship_create(context, data_dict)

def relationship_delete(context, data_dict):
    model = context['model']
    user = context['user']
    relationship = context['relationship']

    pkg1groups = set( relationship.package1.get_groups('publisher') )
    pkg2groups = set (relationship.package2.get_groups('publisher') )
    usergrps =  model.User.get( user ).get_groups('publisher')
    
    if _groups_intersect( usergrps, pkg1groups ) and _groups_intersect( usergrps, pkg2groups ):
        return {'success': True}    
        
    return {'success': False, 'msg': _('User %s not authorized to delete relationship %s') % (str(user),relationship.id)}
        

def group_delete(context, data_dict):
    """
    Group delete permission.  Checks that the user specified is within the group to be deleted
    and also have 'admin' capacity.
    """
    model = context['model']
    user = context['user']

    if not user:
        return {'success': False, 'msg': _('Only members of this group are authorized to delete this group')} 
    
    group = get_group_object(context, data_dict)
    userobj = model.User.get( user )
    if not userobj:
        return {'success': False, 'msg': _('Only members of this group are authorized to delete this group')} 
            
    authorized = _groups_intersect( userobj.get_groups('publisher', 'admin'), [group] )
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete group %s') % (str(user),group.id)}
    else:
        return {'success': True}

def revision_undelete(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def revision_delete(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def task_status_delete(context, data_dict):
    model = context['model']
    user = context['user']

    authorized =  Authorizer().is_sysadmin(unicode(user))
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete task_status') % str(user)}
    else:
        return {'success': True}
