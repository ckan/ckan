#This will be check_access_old
from ckan.logic import check_access
from ckan.logic.auth.create import check_group_auth, package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _

def make_latest_pending_package_active(context, data_dict):
    return package_update(context, data_dict)

def package_update(context, data_dict):
    model = context['model']
    user = context.get('user')
    id = data_dict['id']
    pkg = model.Package.get(id)

    check1 = check_access(pkg, model.Action.EDIT, context)
    if not check1:
        return {'success': False, 'msg': _('User %s not authorized to edit package %s') % (str(user), pkg.id)}
    else:
        check2 = check_group_auth(context,data_dict)
        if not check2:
            return {'success': False, 'msg': _('User %s not authorized to edit these groups') % str(user)}

    return {'success': True}

def package_relationship_update(context, data_dict):
    return package_relationship_create(context, data_dict)

def group_update(context, data_dict):
    model = context['model']
    id = data_dict['id']
    group = model.Group.get(id)
    user = context['user']

    authorized = check_access(group, model.Action.EDIT, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit group %s') % (str(user),id)}
    else:
        return {'success': True}

def user_update(context, data_dict):
    model = context['model']
    user = context['user']
    id = data_dict['id']
    user_obj = model.User.get(id)

    if not (Authorizer().is_sysadmin(unicode(user)) or user == user_obj.name) and \
       not ('reset_key' in data_dict and data_dict['reset_key'] == user_obj.reset_key):
        return {'success': False, 'msg': _('User %s not authorized to edit user %s') % (str(user), id)}

    return {'success': True}


## Modifications for rest api

def package_update_rest(context, data_dict):
    return package_update(context, data_dict)

def group_update_rest(context, data_dict):
    return group_update(context, data_dict)

