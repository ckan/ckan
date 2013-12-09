import sys
import re
from logging import getLogger

from pylons import config
from paste.deploy.converters import asbool

import ckan.plugins as p
import ckan.model as model
from ckan.common import OrderedDict, _, c

import ckan.lib.maintain as maintain

log = getLogger(__name__)


class AuthFunctions:
    ''' This is a private cache used by get_auth_function() and should never be
    accessed directly we will create an instance of it and then remove it.'''
    _functions = {}

    def clear(self):
        ''' clear any stored auth functions. '''
        self._functions.clear()

    def keys(self):
        ''' Return a list of known auth functions.'''
        if not self._functions:
            self._build()
        return self._functions.keys()

    def get(self, function):
        ''' Return the requested auth function. '''
        if not self._functions:
            self._build()
        return self._functions.get(function)

    def _build(self):
        ''' Gather the auth functions.

        First get the default ones in the ckan/logic/auth directory Rather than
        writing them out in full will use __import__ to load anything from
        ckan.auth that looks like it might be an authorisation function'''

        module_root = 'ckan.logic.auth'

        for auth_module_name in ['get', 'create', 'update', 'delete']:
            module_path = '%s.%s' % (module_root, auth_module_name,)
            try:
                module = __import__(module_path)
            except ImportError:
                log.debug('No auth module for action "%s"' % auth_module_name)
                continue

            for part in module_path.split('.')[1:]:
                module = getattr(module, part)

            for key, v in module.__dict__.items():
                if not key.startswith('_'):
                    key = clean_action_name(key)
                    # Whitelist all auth functions defined in
                    # logic/auth/get.py as not requiring an authorized user,
                    # as well as ensuring that the rest do. In both cases, do
                    # nothing if a decorator has already been used to define
                    # the behaviour
                    if not hasattr(v, 'auth_allow_anonymous_access'):
                        if auth_module_name == 'get':
                            v.auth_allow_anonymous_access = True
                        else:
                            v.auth_allow_anonymous_access = False
                    self._functions[key] = v

        # Then overwrite them with any specific ones in the plugins:
        resolved_auth_function_plugins = {}
        fetched_auth_functions = {}
        for plugin in p.PluginImplementations(p.IAuthFunctions):
            for name, auth_function in plugin.get_auth_functions().items():
                name = clean_action_name(name)
                if name in resolved_auth_function_plugins:
                    raise Exception(
                        'The auth function %r is already implemented in %r' % (
                            name,
                            resolved_auth_function_plugins[name]
                        )
                    )
                log.debug('Auth function {0} from plugin {1} was inserted'.format(name, plugin.name))
                resolved_auth_function_plugins[name] = plugin.name
                fetched_auth_functions[name] = auth_function
        # Use the updated ones in preference to the originals.
        self._functions.update(fetched_auth_functions)

_AuthFunctions = AuthFunctions()
#remove the class
del AuthFunctions


def clear_auth_functions_cache():
    _AuthFunctions.clear()
    CONFIG_PERMISSIONS.clear()


def auth_functions_list():
    '''Returns a list of the names of the auth functions available.  Currently
    this is to allow the Auth Audit to know if an auth function is available
    for a given action.'''
    return _AuthFunctions.keys()


def clean_action_name(action_name):
    ''' Used to convert old style action names into new style ones '''
    new_action_name = re.sub('package', 'dataset', action_name)
    # CS: bad_spelling ignore
    return re.sub('licence', 'license', new_action_name)


def is_sysadmin(username):
    ''' Returns True is username is a sysadmin '''
    user = _get_user(username)
    return user and user.sysadmin


def _get_user(username):
    ''' Try to get the user from c, if possible, and fallback to using the DB '''
    if not username:
        return None
    # See if we can get the user without touching the DB
    try:
        if c.userobj and c.userobj.name == username:
            return c.userobj
    except TypeError:
        # c is not available
        pass
    # Get user from the DB
    return model.User.get(username)


def get_group_or_org_admin_ids(group_id):
    if not group_id:
        return []
    group_id = model.Group.get(group_id).id
    q = model.Session.query(model.Member) \
        .filter(model.Member.group_id == group_id) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.state == 'active') \
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

    action = clean_action_name(action)
    auth_function = _AuthFunctions.get(action)
    if auth_function:
        username = context.get('user')
        user = _get_user(username)

        if user:
            # deleted users are always unauthorized
            if user.is_deleted():
                return {'success': False}
            # sysadmins can do anything unless the auth_sysadmins_check
            # decorator was used in which case they are treated like all other
            # users.
            elif user.sysadmin:
                if not getattr(auth_function, 'auth_sysadmins_check', False):
                    return {'success': True}

        # If the auth function is flagged as not allowing anonymous access,
        # and an existing user object is not provided in the context, deny
        # access straight away
        if not getattr(auth_function, 'auth_allow_anonymous_access', False) \
           and not context.get('auth_user_obj'):
            return {'success': False,
                    'msg': '{0} requires an authenticated user'
                            .format(auth_function)
                   }

        return auth_function(context, data_dict)
    else:
        raise ValueError(_('Authorization function not found: %s' % action))


# these are the permissions that roles have
ROLE_PERMISSIONS = OrderedDict([
    ('admin', ['admin']),
    ('editor', ['read', 'delete_dataset', 'create_dataset', 'update_dataset', 'manage_group']),
    ('member', ['read', 'manage_group']),
])


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
    roles = []
    for role in ROLE_PERMISSIONS:
        roles.append(dict(text=trans_role(role), value=role))
    return roles


def roles_trans():
    ''' return dict of roles with translation '''
    roles = {}
    for role in ROLE_PERMISSIONS:
        roles[role] = trans_role(role)
    return roles


def get_roles_with_permission(permission):
    ''' returns the roles with the permission requested '''
    roles = []
    for role in ROLE_PERMISSIONS:
        permissions = ROLE_PERMISSIONS[role]
        if permission in permissions or 'admin' in permissions:
            roles.append(role)
    return roles


def has_user_permission_for_group_or_org(group_id, user_name, permission):
    ''' Check if the user has the given permissions for the group, allowing for
    sysadmin rights and permission cascading down a group hierarchy.

    '''
    if not group_id:
        return False
    group = model.Group.get(group_id)
    if not group:
        return False
    group_id = group.id

    # Sys admins can do anything
    if is_sysadmin(user_name):
        return True

    user_id = get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return False
    if _has_user_permission_for_groups(user_id, permission, [group_id]):
        return True
    # Handle when permissions cascade. Check the user's roles on groups higher
    # in the group hierarchy for permission.
    for capacity in check_config_permission('roles_that_cascade_to_sub_groups'):
        parent_groups = group.get_parent_group_hierarchy(type=group.type)
        group_ids = [group_.id for group_ in parent_groups]
        if _has_user_permission_for_groups(user_id, permission, group_ids,
                                           capacity=capacity):
            return True
    return False


def _has_user_permission_for_groups(user_id, permission, group_ids,
                                    capacity=None):
    ''' Check if the user has the given permissions for the particular
    group (ignoring permissions cascading in a group hierarchy).
    Can also be filtered by a particular capacity.
    '''
    if not group_ids:
        return False
    # get any roles the user has for the group
    q = model.Session.query(model.Member) \
        .filter(model.Member.group_id.in_(group_ids)) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.state == 'active') \
        .filter(model.Member.table_id == user_id)
    if capacity:
        q = q.filter(model.Member.capacity == capacity)
    # see if any role has the required permission
    # admin permission allows anything for the group
    for row in q.all():
        perms = ROLE_PERMISSIONS.get(row.capacity, [])
        if 'admin' in perms or permission in perms:
            return True
    return False


def users_role_for_group_or_org(group_id, user_name):
    ''' Returns the user's role for the group. (Ignores privileges that cascade
    in a group hierarchy.)

    '''
    if not group_id:
        return None
    group_id = model.Group.get(group_id).id

    user_id = get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return None
    # get any roles the user has for the group
    q = model.Session.query(model.Member) \
        .filter(model.Member.group_id == group_id) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.state == 'active') \
        .filter(model.Member.table_id == user_id)
    # return the first role we find
    for row in q.all():
        return row.capacity
    return None


def has_user_permission_for_some_org(user_name, permission):
    ''' Check if the user has the given permission for any organization. '''
    user_id = get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return False
    roles = get_roles_with_permission(permission)

    if not roles:
        return False
    # get any groups the user has with the needed role
    q = model.Session.query(model.Member) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.state == 'active') \
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
    'create_user_via_web': True,
    'roles_that_cascade_to_sub_groups': 'admin',
}

CONFIG_PERMISSIONS = {}


def check_config_permission(permission):
    ''' Returns the permission configuration, usually True/False '''
    # set up perms if not already done
    if not CONFIG_PERMISSIONS:
        for perm in CONFIG_PERMISSIONS_DEFAULTS:
            key = 'ckan.auth.' + perm
            default = CONFIG_PERMISSIONS_DEFAULTS[perm]
            CONFIG_PERMISSIONS[perm] = config.get(key, default)
            if perm == 'roles_that_cascade_to_sub_groups':
                # this permission is a list of strings (space separated)
                CONFIG_PERMISSIONS[perm] = \
                    CONFIG_PERMISSIONS[perm].split(' ') \
                    if CONFIG_PERMISSIONS[perm] else []
            else:
                # most permissions are boolean
                CONFIG_PERMISSIONS[perm] = asbool(CONFIG_PERMISSIONS[perm])
    if permission in CONFIG_PERMISSIONS:
        return CONFIG_PERMISSIONS[permission]
    return False

@maintain.deprecated('Use auth_is_loggedin_user instead')
def auth_is_registered_user():
    '''
    This function is deprecated, please use the auth_is_loggedin_user instead
    '''
    return auth_is_loggedin_user()

def auth_is_loggedin_user():
    ''' Do we have a logged in user '''
    try:
        context_user = c.user
    except TypeError:
        context_user = None
    return bool(context_user)

def auth_is_anon_user(context):
    ''' Is this an anonymous user?
        eg Not logged in if a web request and not user defined in context
        if logic functions called directly

        See ckan/lib/base.py:232 for pylons context object logic
    '''
    try:
        is_anon_user = (not bool(c.user) and bool(c.author))
    except TypeError:
        # No c object set, this is not a call done via the web interface,
        # but directly, eg from an extension
        context_user = context.get('user')
        is_anon_user = not bool(context_user)

    return is_anon_user
