import ckan.logic as logic
from ckan.authz import Authorizer
from ckan.lib.base import _

def package_create(context, data_dict=None):
    model = context['model']
    user = context['user']
    check1 = logic.check_access_old(model.System(), model.Action.PACKAGE_CREATE, context)

    if not check1:
        return {'success': False, 'msg': _('User %s not authorized to create packages') % str(user)}
    else:

        check2 = _check_group_auth(context,data_dict)
        if not check2:
            return {'success': False, 'msg': _('User %s not authorized to edit these groups') % str(user)}

    return {'success': True}

def related_create(context, data_dict=None):
    '''Users must be logged-in to create related items.

    To create a featured item the user must be a sysadmin.
    '''
    model = context['model']
    user = context['user']
    userobj = model.User.get( user )

    if userobj:
        if (data_dict.get('featured', 0) != 0 and
            not Authorizer().is_sysadmin(unicode(user))):

            return {'success': False,
                    'msg': _('You must be a sysadmin to create a featured '
                             'related item')}
        return {'success': True}

    return {'success': False, 'msg': _('You must be logged in to add a related item')}

def resource_create(context, data_dict):
    # resource_create runs through package_update, no need to
    # check users eligibility to add resource to package here.
    model = context['model']
    user = context['user']
    userobj = model.User.get(user)

    if userobj:
        return {'success': True}
    return {'success': False,
            'msg': _('You must be logged in to create a resource')}

def package_relationship_create(context, data_dict):
    model = context['model']
    user = context['user']

    id = data_dict['subject']
    id2 = data_dict['object']
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

    authorized = logic.check_access_old(model.System(), model.Action.GROUP_CREATE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to create groups') % str(user)}
    else:
        return {'success': True}

def authorization_group_create(context, data_dict=None):
    model = context['model']
    user = context['user']

    authorized = logic.check_access_old(model.System(), model.Action.AUTHZ_GROUP_CREATE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to create authorization groups') % str(user)}
    else:
        return {'success': True}

def rating_create(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def user_create(context, data_dict=None):
    model = context['model']
    user = context['user']

    authorized = logic.check_access_old(model.System(), model.Action.USER_CREATE, context)
    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to create users') % str(user)}
    else:
        return {'success': True}


def _check_group_auth(context, data_dict):
    if not data_dict:
        return True

    model = context['model']
    pkg = context.get("package")

    api_version = context.get('api_version') or '1'

    group_blobs = data_dict.get("groups", [])
    groups = set()
    for group_blob in group_blobs:
        # group_blob might be a dict or a group_ref
        if isinstance(group_blob, dict):
            if api_version == '1':
                id = group_blob.get('name')
            else:
                id = group_blob.get('id')
            if not id:
                continue
        else:
            id = group_blob
        grp = model.Group.get(id)
        if grp is None:
            raise logic.NotFound(_('Group was not found.'))
        groups.add(grp)

    if pkg:
        pkg_groups = pkg.get_groups()

        groups = groups - set(pkg_groups)

    for group in groups:
        if not logic.check_access_old(group, model.Action.EDIT, context):
            return False

    return True

## Modifications for rest api

def package_create_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if user in (model.PSEUDO_USER__VISITOR, ''):
        return {'success': False, 'msg': _('Valid API key needed to create a package')}

    return package_create(context, data_dict)

def group_create_rest(context, data_dict):
    model = context['model']
    user = context['user']
    if user in (model.PSEUDO_USER__VISITOR, ''):
        return {'success': False, 'msg': _('Valid API key needed to create a group')}

    return group_create(context, data_dict)

def vocabulary_create(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}

def activity_create(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}

def tag_create(context, data_dict):
    user = context['user']
    return {'success': Authorizer.is_sysadmin(user)}
