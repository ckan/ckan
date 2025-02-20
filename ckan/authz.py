# encoding: utf-8
from __future__ import annotations

import functools
import inspect
import importlib

from collections import defaultdict, OrderedDict
from logging import getLogger
from typing import Any, Callable, Collection, KeysView, Optional, Union
from types import ModuleType

from ckan.common import config, current_user

import ckan.plugins as p
import ckan.model as model
from ckan.common import _

from ckan.types import AuthResult, AuthFunction, DataDict, Context

log = getLogger(__name__)


def get_local_functions(module: ModuleType, include_private: bool = False):
    """Return list of (name, func) tuples.

    Filters out all non-callables and all the items that were
    imported.
    """
    return inspect.getmembers(
        module,
        lambda func: (inspect.isfunction(func) and
                      inspect.getmodule(func) is module and
                      (include_private or not func.__name__.startswith('_'))))


class AuthFunctions:
    ''' This is a private cache used by get_auth_function() and should never be
    accessed directly we will create an instance of it and then remove it.'''
    _functions: dict[str, AuthFunction] = {}

    def clear(self) -> None:
        ''' clear any stored auth functions. '''
        self._functions.clear()

    def keys(self) -> KeysView[str]:
        ''' Return a list of known auth functions.'''
        if not self._functions:
            self._build()
        return self._functions.keys()

    def get(self, function: str) -> Optional[AuthFunction]:
        ''' Return the requested auth function. '''
        if not self._functions:
            self._build()
        return self._functions.get(function)

    @staticmethod
    def _is_chained_auth_function(func: AuthFunction) -> bool:
        '''
        Helper function to check if a function is a chained auth function, i.e.
        it has been decorated with the chain auth function decorator.
        '''
        return getattr(func, 'chained_auth_function', False)

    def _build(self) -> None:
        '''Gather the auth functions.

        First get the default ones in the ckan/logic/auth directory
        Rather than writing them out in full will use
        importlib.import_module to load anything from ckan.auth that
        looks like it might be an authorisation function

        '''

        module_root = 'ckan.logic.auth'

        for auth_module_name in ['get', 'create', 'update', 'delete', 'patch']:
            module = importlib.import_module(
                '.' + auth_module_name, module_root)

            for key, v in get_local_functions(module):
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
        resolved_auth_function_plugins: dict[str, str] = {}
        fetched_auth_functions = {}
        chained_auth_functions = defaultdict(list)
        for plugin in p.PluginImplementations(p.IAuthFunctions):
            for name, auth_function in plugin.get_auth_functions().items():
                if self._is_chained_auth_function(auth_function):
                    chained_auth_functions[name].append(auth_function)
                elif name in resolved_auth_function_plugins:
                    raise Exception(
                        'The auth function %r is already implemented in %r' % (
                            name,
                            resolved_auth_function_plugins[name]
                        )
                    )
                else:
                    resolved_auth_function_plugins[name] = plugin.name
                    fetched_auth_functions[name] = auth_function

        for name, func_list in chained_auth_functions.items():
            if (name not in fetched_auth_functions and
                    name not in self._functions):
                raise Exception('The auth %r is not found for chained auth' % (
                    name))
            # create the chain of functions in the correct order
            for func in reversed(func_list):
                if name in fetched_auth_functions:
                    prev_func = fetched_auth_functions[name]
                else:
                    # fallback to chaining off the builtin auth function
                    prev_func = self._functions[name]

                new_func = (functools.partial(func, prev_func))
                # persisting attributes to the new partial function
                for attribute, value in func.__dict__.items():
                    setattr(new_func, attribute, value)

                fetched_auth_functions[name] = new_func

        # Use the updated ones in preference to the originals.
        self._functions.update(fetched_auth_functions)

_AuthFunctions = AuthFunctions()
#remove the class
del AuthFunctions


def clear_auth_functions_cache() -> None:
    _AuthFunctions.clear()


def auth_functions_list() -> KeysView[str]:
    '''Returns a list of the names of the auth functions available.  Currently
    this is to allow the Auth Audit to know if an auth function is available
    for a given action.'''
    return _AuthFunctions.keys()


def is_sysadmin(username: Optional[str]) -> bool:
    ''' Returns True is username is a sysadmin '''
    user = _get_user(username)
    return bool(user and user.sysadmin)


def _get_user(username: Optional[str]) -> Optional['model.User']:
    '''
    Try to get the user from current_user proxy, if possible.
    If not fallback to using the DB
    '''
    if not username:
        return None
    # See if we can get the user without touching the DB
    try:
        if current_user.name == username:
            return current_user  # type: ignore
    except AttributeError:
        # current_user is anonymous
        pass
    except TypeError:
        # c is not available (py2)
        pass
    except RuntimeError:
        # g is not available (py3)
        pass

    # Get user from the DB
    return model.User.get(username)


def get_group_or_org_admin_ids(group_id: Optional[str]) -> list[str]:
    if not group_id:
        return []
    group = model.Group.get(group_id)
    if not group:
        return []
    q = model.Session.query(model.Member.table_id) \
        .filter(model.Member.group_id == group.id) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.state == 'active') \
        .filter(model.Member.capacity == 'admin')

    # type_ignore_reason: all stored memerships have table_id
    return [a.table_id for a in q]


def is_authorized_boolean(action: str, context: Context, data_dict: Optional[DataDict]=None) -> bool:
    ''' runs the auth function but just returns True if allowed else False
    '''
    outcome = is_authorized(action, context, data_dict=data_dict)
    return outcome.get('success', False)


def is_authorized(action: str, context: Context,
                  data_dict: Optional[DataDict]=None) -> AuthResult:
    if context.get('ignore_auth'):
        return {'success': True}

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
            if isinstance(auth_function, functools.partial):
                name = auth_function.func.__name__
            else:
                name = auth_function.__name__
            return {
                'success': False,
                'msg': 'Action {0} requires an authenticated user'.format(name)
            }

        return auth_function(context, data_dict or {})
    else:
        raise ValueError(_('Authorization function not found: %s' % action))


# these are the permissions that roles have
ROLE_PERMISSIONS: dict[str, list[str]] = OrderedDict([
    ('admin', ['admin', 'membership']),
    ('editor', ['read', 'delete_dataset', 'create_dataset',
                'update_dataset', 'manage_group']),
    ('member', ['read', 'manage_group']),
])


def get_collaborator_capacities() -> Collection[str]:
    if check_config_permission('allow_admin_collaborators'):
        return ('admin', 'editor', 'member')
    else:
        return ('editor', 'member')

_trans_functions: dict[str, Callable[[], str]] = {
    'admin': lambda: _('Admin'),
    'editor': lambda: _('Editor'),
    'member': lambda: _('Member'),
}


def trans_role(role: str) -> str:
    return _trans_functions[role]()


def roles_list() -> list[dict[str, str]]:
    ''' returns list of roles for forms '''
    roles = []
    for role in ROLE_PERMISSIONS:
        roles.append(dict(text=trans_role(role), value=role))
    return roles


def roles_trans() -> dict[str, str]:
    ''' return dict of roles with translation '''
    roles = {}
    for role in ROLE_PERMISSIONS:
        roles[role] = trans_role(role)
    return roles


def get_roles_with_permission(permission: str) -> list[str]:
    ''' returns the roles with the permission requested '''
    roles = []
    for role in ROLE_PERMISSIONS:
        permissions = ROLE_PERMISSIONS[role]
        if permission in permissions or 'admin' in permissions:
            roles.append(role)
    return roles


def has_user_permission_for_group_or_org(group_id: Optional[str],
                                         user_name: Optional[str],
                                         permission: str) -> bool:
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
    capacities = check_config_permission('roles_that_cascade_to_sub_groups')
    assert isinstance(capacities, list)
    # Handle when permissions cascade. Check the user's roles on groups higher
    # in the group hierarchy for permission.
    for capacity in capacities:
        parent_groups = group.get_parent_group_hierarchy(type=group.type)
        group_ids = [group_.id for group_ in parent_groups]
        if _has_user_permission_for_groups(user_id, permission, group_ids,
                                           capacity=capacity):
            return True
    return False


def _has_user_permission_for_groups(
        user_id: str, permission: str, group_ids: list[str],
        capacity: Optional[str]=None) -> bool:
    ''' Check if the user has the given permissions for the particular
    group (ignoring permissions cascading in a group hierarchy).
    Can also be filtered by a particular capacity.
    '''
    if not group_ids:
        return False
    # get any roles the user has for the group
    q: Any = (model.Session.query(model.Member.capacity)
         # type_ignore_reason: attribute has no method
         .filter(model.Member.group_id.in_(group_ids))  # type: ignore
         .filter(model.Member.table_name == 'user')
         .filter(model.Member.state == 'active')
         .filter(model.Member.table_id == user_id))

    if capacity:
        q = q.filter(model.Member.capacity == capacity)
    # see if any role has the required permission
    # admin permission allows anything for the group
    for row in q:
        perms = ROLE_PERMISSIONS.get(row.capacity, [])
        if 'admin' in perms or permission in perms:
            return True
    return False


def users_role_for_group_or_org(
        group_id: Optional[str], user_name: Optional[str]) -> Optional[str]:
    ''' Returns the user's role for the group. (Ignores privileges that cascade
    in a group hierarchy.)

    '''
    if not group_id:
        return None
    group = model.Group.get(group_id)
    if not group:
        return None

    user_id = get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return None
    # get any roles the user has for the group
    q: Any = model.Session.query(model.Member.capacity) \
        .filter(model.Member.group_id == group.id) \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.state == 'active') \
        .filter(model.Member.table_id == user_id)
    # return the first role we find
    for row in q:
        return row.capacity
    return None


def has_user_permission_for_some_org(
        user_name: Optional[str], permission: str) -> bool:
    ''' Check if the user has the given permission for any organization. '''

    # Sys admins can do anything
    if is_sysadmin(user_name):
        return True

    user_id = get_user_id_for_username(user_name, allow_none=True)
    if not user_id:
        return False
    roles = get_roles_with_permission(permission)

    if not roles:
        return False
    # get any groups the user has with the needed role
    q: Any = (model.Session.query(model.Member.group_id)
         .filter(model.Member.table_name == 'user')
         .filter(model.Member.state == 'active')
         # type_ignore_reason: attribute has no method
         .filter(model.Member.capacity.in_(roles))  # type: ignore
         .filter(model.Member.table_id == user_id))
    group_ids = []
    for row in q:
        group_ids.append(row.group_id)
    # if not in any groups has no permissions
    if not group_ids:
        return False

    # see if any of the groups are orgs
    permission_exists: bool = model.Session.query(
        model.Session.query(model.Group)
        .filter(model.Group.is_organization == True)
        .filter(model.Group.state == 'active')
        # type_ignore_reason: attribute has no method
        .filter(model.Group.id.in_(group_ids)).exists()  # type: ignore
    ).scalar()

    return permission_exists


def get_user_id_for_username(
        user_name: Optional[str], allow_none: bool = False) -> Optional[str]:
    ''' Helper function to get user id '''
    # first check if we have the user object already and get from there
    user = _get_user(user_name)
    if user:
        return user.id
    if allow_none:
        return None
    raise Exception('Not logged in user')


def can_manage_collaborators(package_id: str, user_id: str) -> bool:
    '''
    Returns True if a user is allowed to manage the collaborators of a given
    dataset.

    Currently a user can manage collaborators if:

    1. Is an administrator of the organization the dataset belongs to
    2. Is a collaborator with role "admin" (
        assuming :ref:`ckan.auth.allow_admin_collaborators` is set to True)
    3. Is the creator of the dataset and the dataset does not belong to an
        organization (
        requires :ref:`ckan.auth.create_dataset_if_not_in_organization`
        and :ref:`ckan.auth.create_unowned_dataset`)
    '''
    pkg = model.Package.get(package_id)
    if not pkg:
        return False
    owner_org = pkg.owner_org

    if (not owner_org
            and check_config_permission('create_dataset_if_not_in_organization')
            and check_config_permission('create_unowned_dataset')
            and pkg.creator_user_id == user_id):
        # User is the creator of this unowned dataset
        return True

    if has_user_permission_for_group_or_org(
            owner_org, user_id, 'membership'):
        # User is an administrator of the organization the dataset belongs to
        return True

    # Check if user is a collaborator with admin role
    return user_is_collaborator_on_dataset(user_id, pkg.id, 'admin')


def user_is_collaborator_on_dataset(
        user_id: str, dataset_id: str,
        capacity: Optional[Union[str, list[str]]] = None) -> bool:
    '''
    Returns True if the provided user is a collaborator on the provided
    dataset.

    If capacity is provided it restricts the check to the capacity
    provided (eg `admin` or `editor`). Multiple capacities can be
    provided passing a list

    '''

    q = model.Session.query(model.PackageMember) \
        .filter(model.PackageMember.user_id == user_id) \
        .filter(model.PackageMember.package_id == dataset_id)

    if capacity:
        if isinstance(capacity, str):
            capacity = [capacity]
        # type_ignore_reason: attribute has no method
        q = q.filter(model.PackageMember.capacity.in_(capacity))  # type: ignore

    return model.Session.query(q.exists()).scalar()


CONFIG_PERMISSIONS_DEFAULTS: dict[str, Union[bool, str]] = {
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
    'public_activity_stream_detail': False,
    'allow_dataset_collaborators': False,
    'allow_admin_collaborators': False,
    'allow_collaborators_to_change_owner_org': False,
    'create_default_api_keys': False,
}


def check_config_permission(permission: str) -> Union[list[str], bool]:
    '''Returns the configuration value for the provided permission

    Permission is a string indentifying the auth permission (eg
    `anon_create_dataset`), optionally prefixed with `ckan.auth.`.

    The possible values for `permission` are the keys of
    CONFIG_PERMISSIONS_DEFAULTS. These can be overriden in the config file
    by prefixing them with `ckan.auth.`.

    Returns the permission value, generally True or False, except on
    `roles_that_cascade_to_sub_groups` which is a list of strings.

    '''

    key = permission.replace('ckan.auth.', '')

    if key not in CONFIG_PERMISSIONS_DEFAULTS:
        return False

    config_key = 'ckan.auth.' + key

    value = config.get(config_key)

    return value


def auth_is_anon_user(context: Context) -> bool:
    ''' Is this an anonymous user?
        eg Not logged in if a web request and not user defined in context
        if logic functions called directly

        See ckan/lib/base.py:232 for pylons context object logic
    '''
    context_user = context.get('user')
    is_anon_user = not bool(context_user)

    return is_anon_user
