import ckan.logic as logic
import ckan.new_authz as new_authz
from ckan.logic.auth import (get_package_object, get_resource_object,
                            get_group_object, get_user_object,
                            get_resource_object, get_related_object)
from ckan.logic.auth.create import _check_group_auth, package_relationship_create
from ckan.lib.base import _
import ckan.new_authz

def make_latest_pending_package_active(context, data_dict):
    return package_update(context, data_dict)

def package_update(context, data_dict):
    user = context.get('user')
    package = get_package_object(context, data_dict)

    if package.owner_org:
        # if there is an owner org then we must have update_dataset
        # premission for that organization
        check1 = new_authz.has_user_permission_for_group_or_org(package.owner_org, user, 'update_dataset')
    else:
        # If dataset is not owned then we can edit if config permissions allow
        if new_authz.auth_is_registered_user():
            check1 = new_authz.check_config_permission(
                'create_dataset_if_not_in_organization')
        else:
            check1 = new_authz.check_config_permission('anon_create_dataset')
    if not check1:
        return {'success': False, 'msg': _('User %s not authorized to edit package %s') % (str(user), package.id)}
    else:
        check2 = _check_group_auth(context,data_dict)
        if not check2:
            return {'success': False, 'msg': _('User %s not authorized to edit these groups') % str(user)}

    return {'success': True}

def resource_update(context, data_dict):
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
    authorized = package_update(context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit resource %s') % (str(user), resource.id)}
    else:
        return {'success': True}

def package_relationship_update(context, data_dict):
    return package_relationship_create(context, data_dict)

def package_change_state(context, data_dict):
    user = context['user']
    package = get_package_object(context, data_dict)

    # use the logic for package_update
    authorized = new_authz.is_authorized_boolean('package_update', context, data_dict)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to change state of package %s') % (str(user),package.id)}
    else:
        return {'success': True}

def group_update(context, data_dict):
    group = get_group_object(context, data_dict)
    user = context['user']
    authorized = new_authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit group %s') % (str(user),group.id)}
    else:
        return {'success': True}

def organization_update(context, data_dict):
    group = get_group_object(context, data_dict)
    user = context['user']
    authorized = new_authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to edit organization %s') % (user, group.id)}
    else:
        return {'success': True}

def related_update(context, data_dict):
    model = context['model']
    user = context['user']
    if not user:
        return {'success': False, 'msg': _('Only the owner can update a related item')}

    related = get_related_object(context, data_dict)
    userobj = model.User.get( user )
    if not userobj or userobj.id != related.owner_id:
        return {'success': False, 'msg': _('Only the owner can update a related item')}

    # Only sysadmins can change the featured field.
    if ('featured' in data_dict and data_dict['featured'] != related.featured):
        return {'success': False,
                'msg': _('You must be a sysadmin to change a related item\'s '
                         'featured field.')}

    return {'success': True}


def group_change_state(context, data_dict):
    user = context['user']
    group = get_group_object(context, data_dict)

    # use logic for group_update
    authorized = new_authz.is_authorized_boolean('group_update', context, data_dict)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to change state of group %s') % (str(user),group.id)}
    else:
        return {'success': True}

def group_edit_permissions(context, data_dict):
    user = context['user']
    group = get_group_object(context, data_dict)

    if not new_authz.has_user_permission_for_group_or_org(group.id, user, 'update'):
        return {'success': False, 'msg': _('User %s not authorized to edit permissions of group %s') % (str(user),group.id)}
    else:
        return {'success': True}



def user_update(context, data_dict):
    user = context['user']
    user_obj = get_user_object(context, data_dict)

    if not (user == user_obj.name) and \
       not ('reset_key' in data_dict and data_dict['reset_key'] == user_obj.reset_key):
        return {'success': False, 'msg': _('User %s not authorized to edit user %s') % (str(user), user_obj.id)}

    return {'success': True}

def revision_change_state(context, data_dict):
    # FIXME currently only sysadmins can change state
    user = context['user']

    return {'success': False, 'msg': _('User %s not authorized to change state of revision' ) % user}

def task_status_update(context, data_dict):
    # sysadmins only
    user = context['user']
    return {'success': False, 'msg': _('User %s not authorized to update task_status table') % user}

def vocabulary_update(context, data_dict):
    # sysadmins only
    return {'success': False}

def term_translation_update(context, data_dict):
    # sysadmins only
    user = context['user']
    return {'success': False, 'msg': _('User %s not authorized to update term_translation table') % user}


def dashboard_mark_activities_old(context, data_dict):
    # FIXME: This should go through check_access() not call is_authorized()
    # directly, but wait until 2939-orgs is merged before fixing this.
    return ckan.new_authz.is_authorized('dashboard_activity_list',
            context, data_dict)


def send_email_notifications(context, data_dict):
    # Only sysadmins are authorized to send email notifications.
    return {'success': False}


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

def package_owner_org_update(context, data_dict):
    # sysadmins only
    return {'success': False}
