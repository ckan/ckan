import ckan.logic as logic
from ckan.logic.auth import get_package_object, get_group_object, \
    get_user_object, get_resource_object, get_related_object
from ckan.logic.auth.publisher import _groups_intersect
from ckan.logic.auth.publisher.create import package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _

# FIXME: Which is worse, 'from module import foo' or duplicating these
# functions in this module?
from ckan.logic.auth.delete import vocabulary_delete, tag_delete

def package_delete(context, data_dict):
    """
    Delete a package permission. User must be in at least one group that that
    package is also in.
    """
    model = context['model']
    user = context['user']
    package = get_package_object(context, data_dict)
    userobj = model.User.get( user )

    if not userobj or \
       not _groups_intersect( userobj.get_groups('organization'), package.get_groups('organization') ):
        return {'success': False,
                'msg': _('User %s not authorized to delete packages in these group') % str(user)}
    return {'success': True}

def package_relationship_delete(context, data_dict):
    return package_relationship_create(context, data_dict)

def related_delete(context, data_dict):
    model = context['model']
    user = context['user']
    userobj = model.User.get( user )

    if not user or not userobj:
        return {'success': False, 'msg': _('Only the owner can delete a related item')}

    if Authorizer().is_sysadmin(unicode(user)):
        return {'success': True}

    related = get_related_object(context, data_dict)

    if related.datasets:
        package = related.datasets[0]
        if _groups_intersect( userobj.get_groups('organization'), package.get_groups('organization') ):
            return {'success': True}

    if not userobj or userobj.id != related.owner_id:
        return {'success': False, 'msg': _('Only the owner can delete a related item')}

    return {'success': True}


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

    authorized = _groups_intersect( userobj.get_groups('organization', 'admin'), [group] )
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
