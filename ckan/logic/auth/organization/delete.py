import ckan.logic as logic
from ckan.logic.auth import get_package_object, get_group_object, \
    get_user_object, get_resource_object, get_related_object, \
    get_organization_object
from ckan.logic.auth.organization import _groups_intersect
from ckan.logic.auth.organization.create import package_relationship_create
from ckan.authz import Authorizer
from ckan.lib.base import _


def package_delete(context, data_dict):
    """
    Delete a package permission. User must be in at least one group that that
    package is also in.
    """
    model = context['model']
    user = context['user']
    package = get_package_object(context, data_dict)
    userobj = model.User.get( user )

    if Authorizer().is_sysadmin(unicode(user)):
        return {'success': True}

    if not userobj or \
       not _groups_intersect( userobj.get_groups('organization'), package.get_groups('organization') ):
        return {'success': False,
                'msg': _('User %s not authorized to delete packages in these group') % str(user)}
    return {'success': True}

def package_relationship_delete(context, data_dict):
    return package_relationship_create(context, data_dict)

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
        return {'success': False, 'msg': _('User %s not authorized to delete resource %s') % (str(user), resource.id)}
    else:
        return {'success': True}


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

def organization_delete(context, data_dict):
    """
    Organization delete permission.  Checks that the user specified is
    within the organization to be deleted and also have 'admin' capacity.
    """
    model = context['model']
    user = context['user']

    if not user:
        return {'success': False, 'msg': _('Only members of this organization are authorized to delete this group')}

    if Authorizer.is_sysadmin(unicode(user)):
        return {'success': True}

    organization = get_organization_object(context, data_dict)
    userobj = model.User.get(user)
    if not userobj:
        return {'success': False, 'msg': _('Only members of this organization are authorized to delete this group')}

    authorized = _groups_intersect( userobj.get_groups('organization', 'admin'), [organization] )
    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to delete organization %s') % (str(user),organization.id)}
    else:
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

    if Authorizer().is_sysadmin(unicode(user)):
        return {'success': True}

    group = get_group_object(context, data_dict)
    userobj = model.User.get( user )
    if not userobj:
        return {'success': False, 'msg': _('Only members of this group are authorized to delete this group')}

    authorized = _groups_intersect( userobj.get_groups(None, 'admin'), [group] )
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

def vocabulary_delete(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}

def tag_delete(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}
