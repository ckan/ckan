from ckan.logic import check_access_old
from ckan.logic.auth import get_package_object, get_group_object
from ckan.logic.auth.create import package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _

def package_delete(context, data_dict):
    model = context['model']
    user = context['user']
    package = get_package_object(context, data_dict)

    authorized = check_access_old(package, model.Action.PURGE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete package %s') % (str(user),package.id)}
    else:
        return {'success': True}

def package_relationship_delete(context, data_dict):
    can_edit_this_relationship = package_relationship_create(context, data_dict)
    if not can_edit_this_relationship['success']:
        return can_edit_this_relationship
    
    model = context['model']
    user = context['user']
    relationship = context['relationship']

    authorized = check_access_old(relationship, model.Action.PURGE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete relationship %s') % (str(user),relationship.id)}
    else:
        return {'success': True}

def group_delete(context, data_dict):
    model = context['model']
    user = context['user']
    group = get_group_object(context, data_dict)

    authorized = check_access_old(group, model.Action.PURGE, context)
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
