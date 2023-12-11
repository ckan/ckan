# encoding: utf-8
from __future__ import annotations
from contextlib import contextmanager

import functools
import logging
import re
import importlib

from collections import defaultdict
from typing import (Any, Callable, Container, Iterable, Optional,
                    TypeVar, Union, cast, overload)
from typing_extensions import Literal

from werkzeug.datastructures import MultiDict
from sqlalchemy import exc

import six


import ckan.model as model
import ckan.authz as authz
import ckan.lib.navl.dictization_functions as df
import ckan.plugins as p
import ckan.lib.signals as signals

from ckan.common import _, g
from ckan.types import (
    Action, ChainedAction, Model,
    ChainedAuthFunction, DataDict, ErrorDict, Context, FlattenDataDict,
    FlattenKey, Schema, Validator, ValidatorFactory
)

Decorated = TypeVar("Decorated")

log = logging.getLogger(__name__)
_validate = df.validate

_PG_ERR_CODE = {'unique_violation': '23505'}


class NameConflict(Exception):
    pass


class UsernamePasswordError(Exception):
    pass


class ActionError(Exception):
    message: Optional[str]

    def __init__(self, message: Optional[str] = '') -> None:
        self.message = message
        super(ActionError, self).__init__(message)

    def __str__(self):
        msg = self.message
        if not isinstance(msg, str):
            msg = str(msg)
        return six.ensure_text(msg)


class NotFound(ActionError):
    '''Exception raised by logic functions when a given object is not found.

    For example :py:func:`~ckan.logic.action.get.package_show` raises
    :py:exc:`~ckan.plugins.toolkit.ObjectNotFound` if no package with the
    given ``id`` exists.

    '''
    pass


class NotAuthorized(ActionError):
    '''Exception raised when the user is not authorized to call the action.

    For example :py:func:`~ckan.logic.action.create.package_create` raises
    :py:exc:`~ckan.plugins.toolkit.NotAuthorized` if the user is not authorized
    to create packages.
    '''
    pass


class ValidationError(ActionError):
    '''Exception raised by action functions when validating their given
    ``data_dict`` fails.

    '''
    error_dict: ErrorDict

    def __init__(self,
                 errors: Union[str, ErrorDict],
                 error_summary: Optional[dict[str, str]] = None,
                 extra_msg: Optional[str] = None) -> None:
        if not isinstance(errors, dict):
            error_dict: ErrorDict = {'message': errors}
        else:
            error_dict = errors
        # tags errors are a mess so let's clean them up
        if 'tags' in error_dict:
            tag_errors: list[Union[str, dict[str, Any]]] = []
            for error in cast("list[dict[str, Any]]", error_dict['tags']):
                try:
                    tag_errors.append(', '.join(error['name']))
                except KeyError:
                    # e.g. if it is a vocabulary_id error
                    if error:
                        tag_errors.append(error)
            error_dict['tags'] = tag_errors
        self.error_dict = error_dict
        self._error_summary = error_summary
        super(ValidationError, self).__init__(extra_msg)

    @property
    def error_summary(self) -> dict[str, str]:
        ''' autogenerate the summary if not supplied '''
        def summarise(error_dict: ErrorDict) -> dict[str, str]:
            ''' Do some i18n stuff on the error_dict keys '''

            def prettify(field_name: str):
                field_name = re.sub(r'(?<!\w)[Uu]rl(?!\w)', 'URL',
                                    field_name.replace('_', ' ').capitalize())
                return _(field_name.replace('_', ' '))

            summary = {}

            for key, error in error_dict.items():
                if key == 'resources':
                    summary[_('Resources')] = _('Package resource(s) invalid')
                elif key == 'extras':
                    errors_extras = []
                    for item in cast("list[dict[str, Any]]", error):
                        if (item.get('key') and
                                item['key'][0] not in errors_extras):
                            errors_extras.append(item['key'][0])
                    summary[_('Extras')] = ', '.join(errors_extras)
                elif key == 'extras_validation':
                    assert isinstance(error, list)
                    summary[_('Extras')] = error[0]
                elif key == 'tags':
                    assert isinstance(error, list)
                    summary[_('Tags')] = error[0]
                else:
                    assert isinstance(error, list)
                    summary[_(prettify(key))] = error[0]
            return summary

        if self._error_summary:
            return self._error_summary
        return summarise(self.error_dict)

    def __str__(self):
        err_msgs = (super(ValidationError, self).__str__(),
                    self.error_dict)
        return ' - '.join([str(err_msg) for err_msg in err_msgs if err_msg])


def checks_and_delete_if_csrf_token_in_forms(parsed: dict[str, Any]):
    '''
    Checks and delete, if the csrf_token is in "parsed".
    We don't want the csrf_token to be a part of a data_dict
    as it will expose the token to the metadata.
    This way we are deleting the token from every data_dict that fills
    from request.form instead of deleting it separately in every
    view/blueprint.
    '''
    from ckan.common import config

    # WTF_CSRF_FIELD_NAME is added by flask_wtf
    csrf_token = config.get("WTF_CSRF_FIELD_NAME")
    if csrf_token in parsed:
        parsed.pop(csrf_token)
    return parsed


def parse_params(
    params: 'MultiDict[str, Any]',
    ignore_keys: Optional['Container[str]'] = None
) -> dict[str, Union[str, list[str]]]:
    '''Takes a dict and returns it with some values standardised.
    This is done on a dict before calling tuplize_dict on it.
    '''
    parsed = {}
    for key in params:
        if ignore_keys and key in ignore_keys:
            continue
        # flask request has `getlist` instead of pylons' `getall`

        if hasattr(params, 'getall'):
            # type_ignore_reason: pylons legacy
            value = params.getall(key)  # type: ignore
        else:
            value = params.getlist(key)

        # Blank values become ''
        if not value:
            value = ''
        # A list with only one item is stripped of being a list
        if len(value) == 1:
            value = value[0]
        parsed[key] = value

    parsed = checks_and_delete_if_csrf_token_in_forms(parsed)
    return parsed


def clean_dict(data_dict: dict[str, Any]) -> dict[str, Any]:
    '''Takes a dict and if any of the values are lists of dicts,
    the empty dicts are stripped from the lists (recursive).

    e.g.
    >>> clean_dict(
        {'name': u'testgrp4',
         'title': u'',
         'description': u'',
         'packages': [{'name': u'testpkg'}, {'name': u'testpkg'}],
         'extras': [{'key': u'packages', 'value': u'["testpkg"]'},
                    {'key': u'', 'value': u''},
                    {'key': u'', 'value': u''}],
         'state': u'active'}
    {'name': u'testgrp4',
     'title': u'',
     'description': u'',
     'packages': [{'name': u'testpkg'}, {'name': u'testpkg'}],
     'extras': [{'key': u'packages', 'value': u'["testpkg"]'}],
     'state': u'active'}

    '''
    for value in data_dict.values():
        if not isinstance(value, list):
            continue
        for inner_dict in value[:]:
            if isinstance(inner_dict, str):
                break
            if not any(inner_dict.values()):
                value.remove(inner_dict)
            else:
                clean_dict(inner_dict)
    return data_dict


def tuplize_dict(data_dict: dict[str, Any]) -> FlattenDataDict:
    '''Takes a dict with keys of the form 'table__0__key' and converts them
    to a tuple like ('table', 0, 'key').

    Dict should be put through parse_dict before this function, to have
    values standardized.

    May raise a DataError if the format of the key is incorrect.
    '''
    tuplized_dict: FlattenDataDict = {}
    for k, value in data_dict.items():
        key_list = cast("list[Union[str, int]]", k.split('__'))
        for num, key in enumerate(key_list):
            if num % 2 == 1:
                try:
                    key_list[num] = int(key)
                except ValueError:
                    raise df.DataError('Bad key')
        tuplized_dict[tuple(key_list)] = value

    # Sanitize key indexes to make sure they are sequential
    seq_tuplized_dict: FlattenDataDict = {}
    # sequential field indexes grouped by common prefix
    groups: dict[FlattenKey, dict[FlattenKey, int]] = defaultdict(dict)
    for key in sorted(tuplized_dict.keys()):
        new_key = key

        # iterate over even(numeric) parts of the key
        for idx in range(1, len(key), 2):
            # narrow down scope by common prefix
            group = groups[key[:idx]]

            # if the identifier(i.e `(extra, 123)`, `(resource, 9)`) is met for
            # the first time, generate for it next number in the index
            # sequence. Index of the latest added item is always equals to the
            # number of unique identifiers minus one(because list indexation
            # starts from 0 in Python). If identifier already present(i.e, we
            # process `(extra, 10, VALUE)` after processing `(extra, 10,
            # KEY)`), reuse sequential index of this identifier
            seq_index = group.setdefault(key[idx-1:idx+1], len(group))

            # replace the currently processed key segment with computed
            # sequential index
            new_key = new_key[:idx] + (seq_index,) + new_key[idx+1:]

        seq_tuplized_dict[new_key] = tuplized_dict[key]

    return seq_tuplized_dict


def untuplize_dict(tuplized_dict: FlattenDataDict) -> dict[str, Any]:

    data_dict = {}
    for key, value in tuplized_dict.items():
        new_key = '__'.join([str(item) for item in key])
        data_dict[new_key] = value
    return data_dict


def flatten_to_string_key(dict: dict[str, Any]) -> dict[str, Any]:

    flattented = df.flatten_dict(dict)
    return untuplize_dict(flattented)


def _prepopulate_context(context: Optional[Context]) -> Context:
    if context is None:
        context = {}
    context.setdefault('model', cast(Model, model))
    context.setdefault('session', model.Session)

    try:
        user = g.user
    except AttributeError:
        # g.user not set
        user = ""
    except RuntimeError:
        # Outside of request context
        user = ""
    except TypeError:
        # g not registered
        user = ""

    context.setdefault('user', user)
    return context


def check_access(action: str,
                 context: Context,
                 data_dict: Optional[dict[str, Any]] = None) -> Literal[True]:
    '''Calls the authorization function for the provided action

    This is the only function that should be called to determine whether a
    user (or an anonymous request) is allowed to perform a particular action.

    The function accepts a context object, which should contain a 'user' key
    with the name of the user performing the action, and optionally a
    dictionary with extra data to be passed to the authorization function.

    For example::

        check_access('package_update', context, data_dict)

    If not already there, the function will add an `auth_user_obj` key to the
    context object with the actual User object (in case it exists in the
    database). This check is only performed once per context object.

    Raise :py:exc:`~ckan.plugins.toolkit.NotAuthorized` if the user is not
    authorized to call the named action function.

    If the user *is* authorized to call the action, return ``True``.

    :param action: the name of the action function, eg. ``'package_create'``
    :type action: string

    :param context:
    :type context: dict

    :param data_dict:
    :type data_dict: dict

    :raises: :py:exc:`~ckan.plugins.toolkit.NotAuthorized` if the user is not
        authorized to call the named action

    '''

    # Auth Auditing.  We remove this call from the __auth_audit stack to show
    # we have called the auth function
    try:
        audit: Optional[tuple[str, int]] = context.get('__auth_audit', [])[-1]
    except IndexError:
        audit = None
    if audit and audit[0] == action:
        context['__auth_audit'].pop()

    if 'auth_user_obj' not in context:
        context['auth_user_obj'] = None

    context = _prepopulate_context(context)
    if not context.get('ignore_auth'):
        if not context.get('__auth_user_obj_checked'):
            if context["user"] and not context["auth_user_obj"]:
                context['auth_user_obj'] = model.User.get(context['user'])
            context['__auth_user_obj_checked'] = True
    try:
        logic_authorization = authz.is_authorized(action, context, data_dict)
        if not logic_authorization['success']:
            msg = cast(str, logic_authorization.get('msg', ''))
            raise NotAuthorized(msg)
    except NotAuthorized as e:
        log.debug(u'check access NotAuthorized - %s user=%s "%s"',
                  action, context["user"], str(e))
        raise

    log.debug('check access OK - %s user=%s', action, context["user"])
    return True


_actions: dict[str, Action] = {}


def clear_actions_cache() -> None:
    _actions.clear()


def chained_action(func: ChainedAction) -> ChainedAction:
    '''Decorator function allowing action function to be chained.

    This allows a plugin to modify the behaviour of an existing action
    function. A Chained action function must be defined as
    ``action_function(original_action, context, data_dict)`` where the
    first parameter will be set to the action function in the next plugin
    or in core ckan. The chained action may call the original_action
    function, optionally passing different values, handling exceptions,
    returning different values and/or raising different exceptions
    to the caller.

    Usage::

        from ckan.plugins.toolkit import chained_action

        @chained_action
        @side_effect_free
        def package_search(original_action, context, data_dict):
            return original_action(context, data_dict)

    :param func: chained action function
    :type func: callable

    :returns: chained action function
    :rtype: callable

    '''
    # type_ignore_reason: custom attribute
    func.chained_action = True  # type: ignore

    return func


def _is_chained_action(func: Action) -> bool:
    return getattr(func, 'chained_action', False)


def get_action(action: str) -> Action:
    '''Return the named :py:mod:`ckan.logic.action` function.

    For example ``get_action('package_create')`` will normally return the
    :py:func:`ckan.logic.action.create.package_create()` function.

    For documentation of the available action functions, see
    :ref:`api-reference`.

    You should always use ``get_action()`` instead of importing an action
    function directly, because :py:class:`~ckan.plugins.interfaces.IActions`
    plugins can override action functions, causing ``get_action()`` to return a
    plugin-provided function instead of the default one.

    Usage::

        import ckan.plugins.toolkit as toolkit

        # Call the package_create action function:
        toolkit.get_action('package_create')(context, data_dict)

    As the context parameter passed to an action function is commonly::

        context = {'model': ckan.model, 'session': ckan.model.Session,
                   'user': user}

    an action function returned by ``get_action()`` will automatically add
    these parameters to the context if they are not defined.  This is
    especially useful for plugins as they should not really be importing parts
    of ckan eg :py:mod:`ckan.model` and as such do not have access to ``model``
    or ``model.Session``.

    If a ``context`` of ``None`` is passed to the action function then the
    default context dict will be created.

    .. note::

        Many action functions modify the context dict. It can therefore
        not be reused for multiple calls of the same or different action
        functions.

    :param action: name of the action function to return,
        eg. ``'package_create'``
    :type action: string

    :returns: the named action function
    :rtype: callable

    '''

    if _actions:
        if action not in _actions:
            raise KeyError("Action '%s' not found" % action)
        return _actions[action]
    # Otherwise look in all the plugins to resolve all possible First
    # get the default ones in the ckan/logic/action directory Rather
    # than writing them out in full will use importlib.import_module
    # to load anything from ckan.logic.action that looks like it might
    # be an action
    for action_module_name in ['get', 'create', 'update', 'delete', 'patch']:
        module = importlib.import_module(
            '.' + action_module_name, 'ckan.logic.action')
        for k, v in authz.get_local_functions(module):
            _actions[k] = v
            # Allow all actions defined in logic/action/get.py to
            # be side-effect free.
            if action_module_name == 'get' and \
               not hasattr(v, 'side_effect_free'):
                v.side_effect_free = True

    # Then overwrite them with any specific ones in the plugins:
    resolved_action_plugins: dict[str, str] = {}
    fetched_actions = {}
    chained_actions = defaultdict(list)
    for plugin in p.PluginImplementations(p.IActions):
        for name, action_function in plugin.get_actions().items():
            if _is_chained_action(action_function):
                chained_actions[name].append(action_function)
            elif name in resolved_action_plugins:
                raise NameConflict(
                    'The action %r is already implemented in %r' % (
                        name,
                        resolved_action_plugins[name]
                    )
                )
            else:
                resolved_action_plugins[name] = plugin.name
                # Extensions are exempted from the auth audit for now
                # This needs to be resolved later
                # type_ignore_reason: custom attribute
                action_function.auth_audit_exempt = True  # type: ignore
                fetched_actions[name] = action_function
    for name, func_list in chained_actions.items():
        if name not in fetched_actions and name not in _actions:
            # nothing to override from plugins or core
            raise NotFound('The action %r is not found for chained action' % (
                name))
        for func in reversed(func_list):
            # try other plugins first, fall back to core
            prev_func = fetched_actions.get(name, _actions.get(name))
            new_func = functools.partial(func, prev_func)
            # persisting attributes to the new partial function
            for attribute, value in func.__dict__.items():
                setattr(new_func, attribute, value)
            fetched_actions[name] = new_func

    # Use the updated ones in preference to the originals.
    _actions.update(fetched_actions)

    # wrap the functions
    for action_name, _action in _actions.items():
        def make_wrapped(_action: Action, action_name: str):
            def wrapped(context: Optional[Context] = None,
                        data_dict: Optional[DataDict] = None, **kw: Any):
                if kw:
                    log.critical('%s was passed extra keywords %r'
                                 % (_action.__name__, kw))

                context = _prepopulate_context(context)

                if data_dict is None:
                    data_dict = {}

                # Auth Auditing - checks that the action function did call
                # check_access (unless there is no accompanying auth function).
                # We push the action name and id onto the __auth_audit stack
                # before calling the action, and check_access removes it.
                # (We need the id of the action in case the action is wrapped
                # inside an action of the same name, which happens in the
                # datastore)
                context.setdefault('__auth_audit', [])
                context['__auth_audit'].append((action_name, id(_action)))

                # check_access(action_name, context, data_dict=None)
                result = _action(context, data_dict, **kw)
                try:
                    audit = context['__auth_audit'][-1]
                    if audit[0] == action_name and audit[1] == id(_action):
                        if action_name not in authz.auth_functions_list():
                            log.debug('No auth function for %s' % action_name)
                        elif not getattr(_action, 'auth_audit_exempt', False):
                            raise Exception(
                                'Action function {0} did not call its '
                                'auth function'
                                .format(action_name))
                        # remove from audit stack
                        context['__auth_audit'].pop()
                except IndexError:
                    pass

                signals.action_succeeded.send(
                    action_name, context=context, data_dict=data_dict,
                    result=result)
                return result
            return wrapped

        fn = make_wrapped(_action, action_name)
        # we need to mirror the docstring
        fn.__doc__ = _action.__doc__
        # we need to retain the side effect free behaviour
        if getattr(_action, 'side_effect_free', False):
            # type_ignore_reason: custom attribute
            fn.side_effect_free = True  # type: ignore
        _actions[action_name] = fn

    return _actions[action]


@overload
def get_or_bust(data_dict: dict[str, Any], keys: str) -> Any:
    ...


@overload
def get_or_bust(
        data_dict: dict[str, Any], keys: Iterable[str]) -> tuple[Any, ...]:
    ...


def get_or_bust(
        data_dict: dict[str, Any],
        keys: Union[str, Iterable[str]]) -> Union[Any, tuple[Any, ...]]:
    '''Return the value(s) from the given data_dict for the given key(s).

    Usage::

        single_value = get_or_bust(data_dict, 'a_key')
        value_1, value_2 = get_or_bust(data_dict, ['key1', 'key2'])

    :param data_dict: the dictionary to return the values from
    :type data_dict: dictionary

    :param keys: the key(s) for the value(s) to return
    :type keys: either a string or a list

    :returns: a single value from the dict if a single key was given,
        or a tuple of values if a list of keys was given

    :raises: :py:exc:`ckan.logic.ValidationError` if one of the given keys is
        not in the given dictionary

    '''
    if isinstance(keys, str):
        keys = [keys]

    from ckan.logic.schema import create_schema_for_required_keys
    schema = create_schema_for_required_keys(keys)

    data_dict, errors = _validate(data_dict, schema)

    if errors:
        raise ValidationError(errors)

    # preserve original key order
    values = [data_dict[key] for key in keys]
    if len(values) == 1:
        return values[0]
    return tuple(values)


def validate(schema_func: Callable[[], Schema],
             can_skip_validator: bool = False) -> Callable[[Action], Action]:
    ''' A decorator that validates an action function against a given schema
    '''
    def action_decorator(action: Action) -> Action:
        @functools.wraps(action)
        def wrapper(context: Context, data_dict: DataDict):
            if can_skip_validator:
                if context.get('skip_validation'):
                    return action(context, data_dict)

            schema = context.get('schema', schema_func())
            data_dict, errors = _validate(data_dict, schema, context)
            if errors:
                raise ValidationError(errors)
            return action(context, data_dict)
        return wrapper
    return action_decorator


def side_effect_free(action: Decorated) -> Decorated:
    '''A decorator that marks the given action function as side-effect-free.

    Action functions decorated with this decorator can be called with an HTTP
    GET request to the :doc:`Action API </api/index>`. Action functions that
    don't have this decorator must be called with a POST request.

    If your CKAN extension defines its own action functions using the
    :py:class:`~ckan.plugins.interfaces.IActions` plugin interface, you can use
    this decorator to make your actions available with GET requests instead of
    just with POST requests.

    Example::

        import ckan.plugins.toolkit as toolkit

        @toolkit.side_effect_free
        def my_custom_action_function(context, data_dict):
            ...

    (Then implement :py:class:`~ckan.plugins.interfaces.IActions` to register
    your action function with CKAN.)

    '''
    # type_ignore_reason: custom attribute
    action.side_effect_free = True  # type: ignore
    return action


def auth_sysadmins_check(action: Decorated) -> Decorated:
    '''A decorator that prevents sysadmins from being automatically authorized
    to call an action function.

    Normally sysadmins are allowed to call any action function (for example
    when they're using the :doc:`Action API </api/index>` or the web
    interface), if the user is a sysadmin the action function's authorization
    function will not even be called.

    If an action function is decorated with this decorator, then its
    authorization function will always be called, even if the user is a
    sysadmin.

    '''
    # type_ignore_reason: custom attribute
    action.auth_sysadmins_check = True  # type: ignore
    return action


def auth_audit_exempt(action: Decorated) -> Decorated:
    ''' Dirty hack to stop auth audit being done '''
    # type_ignore_reason: custom attribute
    action.auth_audit_exempt = True  # type: ignore
    return action


def auth_allow_anonymous_access(action: Decorated) -> Decorated:
    ''' Flag an auth function as not requiring a logged in user

    This means that check_access won't automatically raise a NotAuthorized
    exception if an authenticated user is not provided in the context. (The
    auth function can still return False if for some reason access is not
    granted).
    '''
    # type_ignore_reason: custom attribute
    action.auth_allow_anonymous_access = True  # type: ignore
    return action


def auth_disallow_anonymous_access(action: Decorated) -> Decorated:
    ''' Flag an auth function as requiring a logged in user

    This means that check_access will automatically raise a NotAuthorized
    exception if an authenticated user is not provided in the context, without
    calling the actual auth function.
    '''
    # type_ignore_reason: custom attribute
    action.auth_allow_anonymous_access = False  # type: ignore
    return action


def chained_auth_function(func: ChainedAuthFunction) -> ChainedAuthFunction:
    '''
    Decorator function allowing authentication functions to be chained.

    This chain starts with the last chained auth function to be registered and
    ends with the original auth function (or a non-chained plugin override
    version). Chained auth functions must accept an extra parameter,
    specifically the next auth function in the chain, for example::

        auth_function(next_auth, context, data_dict).

    The chained auth function may call the next_auth function, optionally
    passing different values, handling exceptions, returning different
    values and/or raising different exceptions to the caller.

    Usage::

        from ckan.plugins.toolkit import chained_auth_function

        @chained_auth_function
        @auth_allow_anonymous_access
        def user_show(next_auth, context, data_dict=None):
            return next_auth(context, data_dict)

    :param func: chained authentication function
    :type func: callable

    :returns: chained authentication function
    :rtype: callable

    '''
    # type_ignore_reason: custom attribute
    func.chained_auth_function = True  # type: ignore
    return func


class UnknownValidator(Exception):
    '''Exception raised when a requested validator function cannot be found.

    '''
    pass


_validators_cache: dict[str, Union[Validator, ValidatorFactory]] = {}


def clear_validators_cache() -> None:
    _validators_cache.clear()


# This function exists mainly so that validators can be made available to
# extensions via ckan.plugins.toolkit.
def get_validator(
        validator: str) -> Union[Validator, ValidatorFactory]:
    '''Return a validator function by name.

    :param validator: the name of the validator function to return,
        eg. ``'package_name_exists'``
    :type validator: string

    :raises: :py:exc:`~ckan.plugins.toolkit.UnknownValidator` if the named
        validator is not found

    :returns: the named validator function
    :rtype: ``types.FunctionType``

    '''
    if not _validators_cache:
        validators = _import_module_functions('ckan.lib.navl.validators')
        _validators_cache.update(validators)
        validators = _import_module_functions('ckan.logic.validators')
        _validators_cache.update(validators)
        converters = _import_module_functions('ckan.logic.converters')
        _validators_cache.update(converters)
        _validators_cache.update({'OneOf': _validators_cache['one_of']})

        for plugin in reversed(list(p.PluginImplementations(p.IValidators))):
            for name, fn in plugin.get_validators().items():
                log.debug('Validator function {0} from plugin {1} was inserted'
                          .format(name, plugin.name))
                _validators_cache[name] = fn
    try:
        return _validators_cache[validator]
    except KeyError:
        raise UnknownValidator('Validator `%s` does not exist' % validator)


def model_name_to_class(model_module: Any, model_name: str) -> Any:
    '''Return the class in model_module that has the same name as the
    received string.

    Raises AttributeError if there's no model in model_module named model_name.
    '''
    model_class_name = model_name.title()
    try:
        return getattr(model_module, model_class_name)
    except AttributeError:
        raise ValidationError({
            "message": "%s isn't a valid model" % model_class_name})


def _import_module_functions(
        module_path: str) -> dict[str, Callable[..., Any]]:
    '''Import a module and get the functions and return them in a dict'''
    module = importlib.import_module(module_path)
    return {
        k: v
        for k, v in authz.get_local_functions(module)
    }


@contextmanager
def guard_against_duplicated_email(email: str):
    try:
        yield
    except exc.IntegrityError as e:
        if e.orig.pgcode == _PG_ERR_CODE["unique_violation"]:
            model.Session.rollback()
            raise ValidationError(
                cast(
                    ErrorDict,
                    {
                        "email": [
                            "The email address '{email}' belongs to "
                            "a registered user.".format(email=email)
                        ]
                    },
                )
            )
        raise


def fresh_context(
    context: Context,
) -> Context:
    """ Copy just the minimum fields into a new context
        for cases in which we reuse the context and
        we want a clean version with minimum fields """
    new_context = {
        k: context[k] for k in (
            'model', 'session', 'user', 'auth_user_obj',
            'ignore_auth', 'defer_commit',
        ) if k in context
    }
    new_context = cast(Context, new_context)
    return new_context
