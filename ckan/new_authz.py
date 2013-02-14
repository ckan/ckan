import sys
from logging import getLogger

from pylons import config, c
from pylons.i18n import _
from paste.deploy.converters import asbool

import ckan.plugins as p
import ckan.model as model

log = getLogger(__name__)

# This is a private cache used by get_auth_function() and should never
# be accessed directly
class AuthFunctions:
    _functions = {}

def is_sysadmin(username):
    ''' returns True is username is a sysadmin '''
    if not username:
        return False
    # see if we can authorise without touching the database
    try:
        if c.userobj and c.userobj.name == username:
            if c.userobj.sysadmin:
                return True
            return False
    except TypeError:
        # c is not available
        pass
    # get user from the database
    user = model.User.get(username)
    if user and user.sysadmin:
        return True
    return False

def get_group_or_org_admin_ids(group_id):
    if not group_id:
        return []
    group_id = model.Group.get(group_id).id
    q = model.Session.query(model.Member) \
        .filter(model.Member.group_id == group_id) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.capacity == 'admin')
    return [a.table_id for a in q.all()]

def is_authorized_boolean(action, context, data_dict=None):
    ''' runs the auth function but just returns True if allowed else False
    '''
    outcome = is_authorized(action, context, data_dict=data_dict)
    return outcome.get('success', False)

def is_authorized(action, context, data_dict=None):
    if context.get('ignore_auth'):
        return {'success': True}

    # sysadmins can do anything
    if is_sysadmin(context.get('user')):
        return {'success': True}

    auth_function = _get_auth_function(action)
    if auth_function:
        return auth_function(context, data_dict)
    else:
        raise ValueError(_('Authorization function not found: %s' % action))

# these are the permissions that roles have
ROLE_PERMISSIONS = {
    'admin': ['admin'],
    'editor': ['read', 'delete_dataset', 'create_dataset', 'update_dataset'],
    'member': ['read'],
}

def _trans_role_admin():
    return _('Admin')

def _trans_role_editor():
    return _('Editor')

def _trans_role_member():
    return _('Member')

def trans_role(role):
    module = sys.modules[__name__]
    return getattr(module, '_trans_role_%s' % role)()


def roles_list():
    ''' returns list of roles for forms '''
    out = []
    for role in ROLE_PERMISSIONS:
        out.append(dict(text=trans_role(role), value=role))
    return out


def get_roles_with_permission(permission):
    ''' returns the roles with the permission requested '''
    roles = []
    for role in ROLE_PERMISSIONS:
        permissions = ROLE_PERMISSIONS[role]
        if permission in permissions or 'admin' in permissions:
            roles.append(role)
    return roles


def has_user_permission_for_group_or_org(group_id, user_name, permission):
    ''' Check if the user has the given permission for the group '''
    if not group_id:
        return False
    group_id = model.Group.get(group_id).id

    # Sys admins can do anything
    if is_sysadmin(user_name):
        return True

    user_id = get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return False
    # get any roles the user has for the group
    q = model.Session.query(model.Member) \
        .filter(model.Member.group_id == group_id) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.table_id == user_id)
    # see if any role has the required permission
    # admin permission allows anything for the group
    for row in q.all():
        perms = ROLE_PERMISSIONS.get(row.capacity, [])
        if 'admin' in perms or permission in perms:
            return True
    return False

def has_user_permission_for_some_org(user_name, permission):
    ''' Check if the user has the given permission for the group '''
    user_id = get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return False
    roles = get_roles_with_permission(permission)

    if not roles:
        return False
    # get any groups the user has with the needed role
    q = model.Session.query(model.Member) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.capacity.in_(roles)) \
        .filter(model.Member.table_id == user_id)
    group_ids = []
    for row in q.all():
        group_ids.append(row.group_id)
    # if not in any groups has no permissions
    if not group_ids:
        return False

    # see if any of the groups are orgs
    q = model.Session.query(model.Group) \
        .filter(model.Group.is_organization == True) \
        .filter(model.Group.state == 'active') \
        .filter(model.Group.id.in_(group_ids))

    return bool(q.count())

def get_user_id_for_username(user_name, allow_none=False):
    ''' Helper function to get user id '''
    # first check if we have the user object already and get from there
    try:
        if c.userobj and c.userobj.name == user_name:
            return c.userobj.id
    except TypeError:
        # c is not available
        pass
    user = model.User.get(user_name)
    if user:
        return user.id
    if allow_none:
        return None
    raise Exception('Not logged in user')

def _get_auth_function(action, profile=None):
    from pylons import config

    if AuthFunctions._functions:
        return AuthFunctions._functions.get(action)

    # Otherwise look in all the plugins to resolve all possible
    # First get the default ones in the ckan/logic/auth directory
    # Rather than writing them out in full will use __import__
    # to load anything from ckan.auth that looks like it might
    # be an authorisation function

    # We will load the auth profile from settings
    module_root = 'ckan.logic.auth'
    if profile is not None:
        auth_profile = profile
    else:
        auth_profile = config.get('ckan.auth.profile', '')

    if auth_profile:
        module_root = '%s.%s' % (module_root, auth_profile)

    log.debug('Using auth profile at %s' % module_root)

    for auth_module_name in ['get', 'create', 'update','delete']:
        module_path = '%s.%s' % (module_root, auth_module_name,)
        try:
            module = __import__(module_path)
        except ImportError,e:
            log.debug('No auth module for action "%s"' % auth_module_name)
            continue

        for part in module_path.split('.')[1:]:
            module = getattr(module, part)

        for key, v in module.__dict__.items():
            if not key.startswith('_'):
                AuthFunctions._functions[key] = v

    # Then overwrite them with any specific ones in the plugins:
    resolved_auth_function_plugins = {}
    fetched_auth_functions = {}
    for plugin in p.PluginImplementations(p.IAuthFunctions):
        for name, auth_function in plugin.get_auth_functions().items():
            if name in resolved_auth_function_plugins:
                raise Exception(
                    'The auth function %r is already implemented in %r' % (
                        name,
                        resolved_auth_function_plugins[name]
                    )
                )
            log.debug('Auth function %r was inserted', plugin.name)
            resolved_auth_function_plugins[name] = plugin.name
            fetched_auth_functions[name] = auth_function
    # Use the updated ones in preference to the originals.
    AuthFunctions._functions.update(fetched_auth_functions)
    return AuthFunctions._functions.get(action)

CONFIG_PERMISSIONS_DEFAULTS = {
    # permission and default
    # these are prefixed with ckan.auth. in config to override
    'anon_create_dataset': False,
    'create_dataset_if_not_in_organization': True,
    'create_unowned_dataset': True,
    'user_create_groups': True,
    'user_create_organizations': True,
    'user_delete_groups': True,
    'user_delete_organizations': True,
    'create_user_via_api': False,
    'create_user': True,
}

CONFIG_PERMISSIONS = {}

def check_config_permission(permission):
    ''' Returns the permission True/False based on config '''
    # set up perms if not already done
    if not CONFIG_PERMISSIONS:
        for perm in CONFIG_PERMISSIONS_DEFAULTS:
            key = 'ckan.auth.' + perm
            default = CONFIG_PERMISSIONS_DEFAULTS[perm]
            CONFIG_PERMISSIONS[perm] = asbool(config.get(key, default))
    if permission in CONFIG_PERMISSIONS:
        return CONFIG_PERMISSIONS[permission]
    return False



def auth_is_registered_user():
    ''' Do we have a logged in user '''
    try:
        context_user = c.user
    except TypeError:
        context_user = None
    return bool(context_user)
