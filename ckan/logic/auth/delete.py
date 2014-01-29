import ckan.logic as logic
import ckan.new_authz as new_authz
from ckan.logic.auth import get_group_object, get_related_object
from ckan.logic.auth import get_resource_object
import ckan.logic.auth.create as _auth_create
import ckan.logic.auth.update as _auth_update
from ckan.lib.base import _


def user_delete(context, data_dict):
    # sysadmins only
    return {'success': False}


def package_delete(context, data_dict):
    # Defer auhtorization for package_delete to package_update, as deletions
    # are essentially changing the state field
    return _auth_update.package_update(context, data_dict)

def resource_delete(context, data_dict):
    model = context['model']
    user = context.get('user')
    resource = get_resource_object(context, data_dict)

    # check authentication against package
    query = model.Session.query(model.Package)\
        .join(model.ResourceGroup)\
        .join(model.Resource)\
        .filter(model.ResourceGroup.id == resource.resource_group_id)
    pkg = query.first()
    if not pkg:
        raise logic.NotFound(_('No package found for this resource, cannot check auth.'))

    pkg_dict = {'id': pkg.id}
    authorized = package_delete(context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete resource %s') % (user, resource.id)}
    else:
        return {'success': True}


def related_delete(context, data_dict):
    model = context['model']
    user = context['user']
    if not user:
        return {'success': False, 'msg': _('Only the owner can delete a related item')}

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
    user = context['user']
    relationship = context['relationship']

    # If you can create this relationship the you can also delete it
    authorized = new_authz.is_authorized_boolean('package_relationship_create', context, data_dict)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete relationship %s') % (user ,relationship.id)}
    else:
        return {'success': True}

def group_delete(context, data_dict):
    group = get_group_object(context, data_dict)
    user = context['user']
    if not new_authz.check_config_permission('user_delete_groups'):
        return {'success': False,
            'msg': _('User %s not authorized to delete groups') % user}
    authorized = new_authz.has_user_permission_for_group_or_org(
        group.id, user, 'delete')
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete group %s') % (user ,group.id)}
    else:
        return {'success': True}

def group_purge(context, data_dict):
    # Only sysadmins are authorized to purge groups.
    return {'success': False}

def organization_purge(context, data_dict):
    # Only sysadmins are authorized to purge organizations.
    return {'success': False}

def organization_delete(context, data_dict):
    group = get_group_object(context, data_dict)
    user = context['user']
    if not new_authz.check_config_permission('user_delete_organizations'):
        return {'success': False,
            'msg': _('User %s not authorized to delete organizations') % user}
    authorized = new_authz.has_user_permission_for_group_or_org(
        group.id, user, 'delete')
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete organization %s') % (user ,group.id)}
    else:
        return {'success': True}

def revision_undelete(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def revision_delete(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def task_status_delete(context, data_dict):
    # sysadmins only
    user = context['user']
    return {'success': False, 'msg': _('User %s not authorized to delete task_status') % user}

def vocabulary_delete(context, data_dict):
    # sysadmins only
    return {'success': False}

def tag_delete(context, data_dict):
    # sysadmins only
    return {'success': False}

def group_member_delete(context, data_dict):
    ## just return true as logic runs through member_delete
    return {'success': True}

def organization_member_delete(context, data_dict):
    ## just return true as logic runs through member_delete
    return {'success': True}

def member_delete(context, data_dict):
    return _auth_create.member_create(context, data_dict)
