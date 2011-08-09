from ckan.logic import check_access_old
from ckan.authz import Authorizer
from ckan.lib.base import _


def package_create(context, data_dict=None):
    model = context['model']
    user = context['user']

    check1 = check_access_old(model.System(), model.Action.PACKAGE_CREATE, context)
    if not check1:
        return {'success': False, 'msg': _('User %s not authorized to create packages') % str(user)}
    else:
        check2 = check_group_auth(context,data_dict)
        if not check2:
            return {'success': False, 'msg': _('User %s not authorized to edit these groups') % str(user)}

    return {'success': True}

def resource_create(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def package_relationship_create(context, data_dict):
    model = context['model']
    user = context['user']

    id = data_dict['id']
    id2 = data_dict['id2']
    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)

    authorized = Authorizer().\
                    authorized_package_relationship(\
                    user, pkg1, pkg2, action=model.Action.EDIT)
    
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit these packages') % str(user)}
    else:
        return {'success': True}

def group_create(context, data_dict=None):
    model = context['model']
    user = context['user']
   
    authorized = check_access_old(model.System(), model.Action.GROUP_CREATE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to create groups') % str(user)}
    else:
        return {'success': True}

def rating_create(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def user_create(context, data_dict=None):
    model = context['model']
    user = context['user']
   
    authorized = check_access_old(model.System(), model.Action.USER_CREATE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to create users') % str(user)}
    else:
        return {'success': True}

def check_group_auth(context, data_dict):
    model = context['model']
    pkg = context.get("package")

    ## hack as api does not allow groups
    if context.get("allow_partial_update"):
        return True

    group_dicts = data_dict.get("groups", [])
    groups = set()
    for group_dict in group_dicts:
        id = group_dict.get('id')
        if not id:
            continue
        grp = model.Group.get(id)
        if grp is None:
            raise NotFound(_('Group was not found.'))
        groups.add(grp)

    if pkg:
        groups = groups - set(pkg.groups)

    for group in groups:
        if not check_access_old(group, model.Action.EDIT, context):
            return False

    return True

## Modifications for rest api

def package_create_rest(context, data_dict):
    return package_create(context, data_dict)

def group_create_rest(context, data_dict):
    return group_create(context, data_dict)
