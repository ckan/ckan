from ckan.logic import check_access_old
from ckan.logic.auth.create import check_group_auth, package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _

def make_latest_pending_package_active(context, data_dict):
    return package_update(context, data_dict)

def package_update(context, data_dict):
    model = context['model']
    user = context.get('user')
    if not 'package' in context:
        id = data_dict.get('id',None)
        package = model.Package.get(id)
        if not package:
            raise NotFound
    else:
        package = context['package']

    check1 = check_access_old(package, model.Action.EDIT, context)
    if not check1:
        return {'success': False, 'msg': _('User %s not authorized to edit package %s') % (str(user), package.id)}
    else:
        check2 = check_group_auth(context,data_dict)
        if not check2:
            return {'success': False, 'msg': _('User %s not authorized to edit these groups') % str(user)}

    return {'success': True}

def package_relationship_update(context, data_dict):
    return package_relationship_create(context, data_dict)

def package_change_state(context, data_dict):
    model = context['model']
    package = context['package']
    user = context['user']

    authorized = check_access_old(package, model.Action.CHANGE_STATE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to change state of package %s') % (str(user),package.id)}
    else:
        return {'success': True}

def package_edit_permissions(context, data_dict):
    model = context['model']
    package = context['package']
    user = context['user']

    authorized = check_access_old(package, model.Action.EDIT_PERMISSIONS, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit permissions of package %s') % (str(user),package.id)}
    else:
        return {'success': True}

def group_update(context, data_dict):
    model = context['model']
    user = context['user']
    if not 'group' in context:
        id = data_dict.get('id',None)
        group = model.Group.get(id)
        if not group:
            raise NotFound
    else:
        group = context['group']

    authorized = check_access_old(group, model.Action.EDIT, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit group %s') % (str(user),group.id)}
    else:
        return {'success': True}

def group_change_state(context, data_dict):
    model = context['model']
    group = context['group']
    user = context['user']

    authorized = check_access_old(group, model.Action.CHANGE_STATE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to change state of group %s') % (str(user),group.id)}
    else:
        return {'success': True}

def group_edit_permissions(context, data_dict):
    model = context['model']
    group = context['group']
    user = context['user']

    authorized = check_access_old(group, model.Action.EDIT_PERMISSIONS, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit permissions of group %s') % (str(user),group.id)}
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

def revision_change_state(context, data_dict):
    model = context['model']
    user = context['user']

    authorized = Authorizer().is_authorized(user, model.Action.CHANGE_STATE, model.Revision)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to change state of revision' ) % str(user)}
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

