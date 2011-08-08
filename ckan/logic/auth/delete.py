#This will be check_access_old
from ckan.logic import check_access
from ckan.logic.auth.create import package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _

def package_delete(context, data_dict):
    model = context['model']
    user = context['user']
    if not 'package' in context:
        id = data_dict.get('id',None)
        package = model.Package.get(id)
        if not package:
            raise NotFound
    else:
        package = context['package']

    #TODO: model.Action.CHANGE_STATE or model.Action.PURGE?
    authorized = check_access(package, model.Action.PURGE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete package %s') % (str(user),package.id)}
    else:
        return {'success': True}

def package_relationship_delete(context, data_dict):
    return package_relationship_create(context, data_dict)

def relationship_delete(context, data_dict):
    model = context['model']
    user = context['user']
    relationship = context['relationship']

    authorized = check_access(relationship, model.Action.PURGE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete relationship %s') % (str(user),relationship.id)}
    else:
        return {'success': True}

def group_delete(context, data_dict):
    model = context['model']
    user = context['user']
    if not 'group' in context:
        id = data_dict.get('id',None)
        group = model.Group.get(id)
        if not group:
            raise NotFound
    else:
        group = context['group']

    authorized = check_access(group, model.Action.PURGE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete group %s') % (str(user),group.id)}
    else:
        return {'success': True}

def revision_undelete(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def revision_delete(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

