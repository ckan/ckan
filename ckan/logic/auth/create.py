#This will be check_access_old
from ckan.logic import check_access
from ckan.authz import Authorizer



def package_create(context, data_dict=None):
    model = context['model']

    success = (check_access(model.System(), model.Action.PACKAGE_CREATE, context) and
               check_group_auth(context,data_dict))
    return {'success':  success}

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

    return {'success': authorized}

def group_create(context, data_dict=None):
    model = context['model']

    return {'success':  check_access(model.System(), model.Action.GROUP_CREATE, context)}

def rating_create(context, data_dict):
    # No authz check in the logic function
    return {'success': True}

def user_create(context, data_dict=None):
    model = context['model']

    return {'success': check_access(model.System(), model.Action.USER_CREATE, context)}

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
        check_access(group, model.Action.EDIT, context)

    return True

## Modifications for rest api

def package_create_rest(context, data_dict):
    return package_create(context, data_dict)

def group_create_rest(context, data_dict):
    return group_create(context, data_dict)
