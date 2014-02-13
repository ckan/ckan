import ckan.logic as logic
import ckan.new_authz as new_authz
import ckan.logic.auth as logic_auth
from ckan.common import _

# FIXME this import is evil and should be refactored
from ckan.logic.auth.create import _check_group_auth


def make_latest_pending_package_active(context, data_dict):
    return new_authz.is_authorized('package_update', context, data_dict)

@logic.auth_allow_anonymous_access
def package_update(context, data_dict):
    user = context.get('user')
    package = logic_auth.get_package_object(context, data_dict)

    if package.owner_org:
        # if there is an owner org then we must have update_dataset
        # permission for that organization
        check1 = new_authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'update_dataset'
        )
    else:
        # If dataset is not owned then we can edit if config permissions allow
        if not new_authz.auth_is_anon_user(context):
            check1 = new_authz.check_config_permission(
                'create_dataset_if_not_in_organization')
        else:
            check1 = new_authz.check_config_permission('anon_create_dataset')
    if not check1:
        return {'success': False,
                'msg': _('User %s not authorized to edit package %s') %
                        (str(user), package.id)}
    else:
        check2 = _check_group_auth(context, data_dict)
        if not check2:
            return {'success': False,
                    'msg': _('User %s not authorized to edit these groups') %
                            (str(user))}

    return {'success': True}

def package_resource_reorder(context, data_dict):
    ## the action function runs package update so no need to run it twice
    return {'success': True}

def resource_update(context, data_dict):
    model = context['model']
    user = context.get('user')
    resource = logic_auth.get_resource_object(context, data_dict)

    # check authentication against package
    query = model.Session.query(model.Package)\
        .join(model.ResourceGroup)\
        .join(model.Resource)\
        .filter(model.ResourceGroup.id == resource.resource_group_id)
    pkg = query.first()
    if not pkg:
        raise logic.NotFound(
            _('No package found for this resource, cannot check auth.')
        )

    pkg_dict = {'id': pkg.id}
    authorized = new_authz.is_authorized('package_update', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit resource %s') %
                        (str(user), resource.id)}
    else:
        return {'success': True}


def package_relationship_update(context, data_dict):
    return new_authz.is_authorized('package_relationship_create',
                                   context,
                                   data_dict)


def package_change_state(context, data_dict):
    user = context['user']
    package = logic_auth.get_package_object(context, data_dict)

    # use the logic for package_update
    authorized = new_authz.is_authorized_boolean('package_update',
                                                 context,
                                                 data_dict)
    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to change state of package %s') %
                    (str(user), package.id)
        }
    else:
        return {'success': True}


def group_update(context, data_dict):
    group = logic_auth.get_group_object(context, data_dict)
    user = context['user']
    authorized = new_authz.has_user_permission_for_group_or_org(group.id,
                                                                user,
                                                                'update')
    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit group %s') %
                        (str(user), group.id)}
    else:
        return {'success': True}


def organization_update(context, data_dict):
    group = logic_auth.get_group_object(context, data_dict)
    user = context['user']
    authorized = new_authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')
    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit organization %s') %
                        (user, group.id)}
    else:
        return {'success': True}


def related_update(context, data_dict):
    model = context['model']
    user = context['user']
    if not user:
        return {'success': False,
                'msg': _('Only the owner can update a related item')}

    related = logic_auth.get_related_object(context, data_dict)
    userobj = model.User.get(user)
    if not userobj or userobj.id != related.owner_id:
        return {'success': False,
                'msg': _('Only the owner can update a related item')}

    # Only sysadmins can change the featured field.
    if ('featured' in data_dict and data_dict['featured'] != related.featured):
        return {'success': False,
                'msg': _('You must be a sysadmin to change a related item\'s '
                         'featured field.')}

    return {'success': True}


def group_change_state(context, data_dict):
    user = context['user']
    group = logic_auth.get_group_object(context, data_dict)

    # use logic for group_update
    authorized = new_authz.is_authorized_boolean('group_update',
                                                 context,
                                                 data_dict)
    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to change state of group %s') %
                    (str(user), group.id)
        }
    else:
        return {'success': True}


def group_edit_permissions(context, data_dict):
    user = context['user']
    group = logic_auth.get_group_object(context, data_dict)

    authorized = new_authz.has_user_permission_for_group_or_org(group.id,
                                                                user,
                                                                'update')

    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit permissions of group %s') %
                        (str(user), group.id)}
    else:
        return {'success': True}


@logic.auth_allow_anonymous_access
def user_update(context, data_dict):
    user = context['user']

    # FIXME: We shouldn't have to do a try ... except here, validation should
    # have ensured that the data_dict contains a valid user id before we get to
    # authorization.
    try:
        user_obj = logic_auth.get_user_object(context, data_dict)
    except logic.NotFound:
        return {'success': False, 'msg': _('User not found')}

    # If the user has a valid reset_key in the db, and that same reset key
    # has been posted in the data_dict, we allow the user to update
    # her account without using her password or API key.
    if user_obj.reset_key and 'reset_key' in data_dict:
        if user_obj.reset_key == data_dict['reset_key']:
            return {'success': True}

    if not user:
        return {'success': False,
                'msg': _('Have to be logged in to edit user')}

    if user == user_obj.name:
        # Allow users to update their own user accounts.
        return {'success': True}
    else:
        # Don't allow users to update other users' accounts.
        return {'success': False,
                'msg': _('User %s not authorized to edit user %s') %
                        (user, user_obj.id)}


def revision_change_state(context, data_dict):
    # FIXME currently only sysadmins can change state
    user = context['user']
    return {
        'success': False,
        'msg': _('User %s not authorized to change state of revision') % user
    }


def task_status_update(context, data_dict):
    # sysadmins only
    user = context['user']
    return {
        'success': False,
        'msg': _('User %s not authorized to update task_status table') % user
    }


def vocabulary_update(context, data_dict):
    # sysadmins only
    return {'success': False}


def term_translation_update(context, data_dict):
    # sysadmins only
    user = context['user']
    return {
        'success': False,
        'msg': _('User %s not authorized to update term_translation table') % user
    }


def dashboard_mark_activities_old(context, data_dict):
    return new_authz.is_authorized('dashboard_activity_list',
                                   context,
                                   data_dict)


def send_email_notifications(context, data_dict):
    # Only sysadmins are authorized to send email notifications.
    return {'success': False}


## Modifications for rest api

def package_update_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if user in (model.PSEUDO_USER__VISITOR, ''):
        return {'success': False,
                'msg': _('Valid API key needed to edit a package')}

    return new_authz.is_authorized('package_update', context, data_dict)


def group_update_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if user in (model.PSEUDO_USER__VISITOR, ''):
        return {'success': False,
                'msg': _('Valid API key needed to edit a group')}

    return group_update(context, data_dict)


def package_owner_org_update(context, data_dict):
    # sysadmins only
    return {'success': False}


def bulk_update_private(context, data_dict):
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = new_authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}


def bulk_update_public(context, data_dict):
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = new_authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}


def bulk_update_delete(context, data_dict):
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = new_authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}
