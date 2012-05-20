import ckan.logic as logic
from ckan.logic.auth import get_package_object, get_group_object, get_related_object
from ckan.logic.auth.create import package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _

def package_delete(context, data_dict):
    model = context['model']
    user = context['user']
    package = get_package_object(context, data_dict)

    authorized = logic.check_access_old(package, model.Action.PURGE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete package %s') % (str(user),package.id)}
    else:
        return {'success': True}


def related_delete(context, data_dict):
    model = context['model']
    user = context['user']
    if not user:
        return {'success': False, 'msg': _('Only the owner can delete a related item')}

    if Authorizer().is_sysadmin(unicode(user)):
        return {'success': True}

    related = get_related_object(context, data_dict)
    userobj = model.User.get( user )

    if related.datasets:
        package = related.datasets[0]

        pkg_dict = { 'id': package.id }
        authorized = package_delete(context, pkg_dict).get('success')
        if authorized:
            return {'success': True}

    if not userobj or userobj.id != related.owner_id:
        return {'success': False, 'msg': _('Only the owner can delete a related item')}

    return {'success': True}


def package_relationship_delete(context, data_dict):
    can_edit_this_relationship = package_relationship_create(context, data_dict)
    if not can_edit_this_relationship['success']:
        return can_edit_this_relationship

    model = context['model']
    user = context['user']
    relationship = context['relationship']

    authorized = logic.check_access_old(relationship, model.Action.PURGE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete relationship %s') % (str(user),relationship.id)}
    else:
        return {'success': True}

def group_delete(context, data_dict):
    model = context['model']
    user = context['user']
    group = get_group_object(context, data_dict)

    authorized = logic.check_access_old(group, model.Action.PURGE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete group %s') % (str(user),group.id)}
    else:
        return {'success': True}

def revision_undelete(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def revision_delete(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def task_status_delete(context, data_dict):
    user = context['user']

    authorized =  Authorizer().is_sysadmin(unicode(user))
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete task_status') % str(user)}
    else:
        return {'success': True}

def vocabulary_delete(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}

def tag_delete(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}
