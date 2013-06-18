import functools
import logging
import types
import re

import formencode.validators

import ckan.model as model
import ckan.new_authz as new_authz
import ckan.lib.navl.dictization_functions as df
import ckan.plugins as p

from ckan.common import _, c

log = logging.getLogger(__name__)
_validate = df.validate


class AttributeDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('No such attribute %r' % name)

    def __setattr__(self, name, value):
        raise AttributeError(
            'You cannot set attributes of this object directly'
        )


class ActionError(Exception):
    def __init__(self, extra_msg=None):
        self.extra_msg = extra_msg

    def __str__(self):
        err_msgs = (super(ActionError, self).__str__(),
                    self.extra_msg)
        return ' - '.join([str(err_msg) for err_msg in err_msgs if err_msg])


class NotFound(ActionError):
    pass


class NotAuthorized(ActionError):
    pass


class ValidationError(ActionError):

    def __init__(self, error_dict, error_summary=None, extra_msg=None):
        if not isinstance(error_dict, dict):
            error_dict = {'message': error_dict}
        # tags errors are a mess so let's clean them up
        if 'tags' in error_dict:
            tag_errors = []
            for error in error_dict['tags']:
                try:
                    tag_errors.append(', '.join(error['name']))
                except KeyError:
                    pass
            error_dict['tags'] = tag_errors
        self.error_dict = error_dict
        self._error_summary = error_summary
        self.extra_msg = extra_msg

    @property
    def error_summary(self):
        ''' autogenerate the summary if not supplied '''
        def summarise(error_dict):
            ''' Do some i18n stuff on the error_dict keys '''

            def prettify(field_name):
                field_name = re.sub('(?<!\w)[Uu]rl(?!\w)', 'URL',
                                    field_name.replace('_', ' ').capitalize())
                return _(field_name.replace('_', ' '))

            summary = {}
            for key, error in error_dict.iteritems():
                if key == 'resources':
                    summary[_('Resources')] = _('Package resource(s) invalid')
                elif key == 'extras':
                    summary[_('Extras')] = _('Missing Value')
                elif key == 'extras_validation':
                    summary[_('Extras')] = error[0]
                elif key == 'tags':
                    summary[_('Tags')] = error[0]
                else:
                    summary[_(prettify(key))] = error[0]
            return summary

        if self._error_summary:
            return self._error_summary
        return summarise(self.error_dict)

    def __str__(self):
        err_msgs = (super(ValidationError, self).__str__(),
                    self.error_dict)
        return ' - '.join([str(err_msg) for err_msg in err_msgs if err_msg])

log = logging.getLogger(__name__)


def parse_params(params, ignore_keys=None):
    '''Takes a dict and returns it with some values standardised.
    This is done on a dict before calling tuplize_dict on it.
    '''
    parsed = {}
    for key in params:
        if ignore_keys and key in ignore_keys:
            continue
        value = params.getall(key)
        # Blank values become ''
        if not value:
            value = ''
        # A list with only one item is stripped of being a list
        if len(value) == 1:
            value = value[0]
        parsed[key] = value
    return parsed


def clean_dict(data_dict):
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
    for key, value in data_dict.items():
        if not isinstance(value, list):
            continue
        for inner_dict in value[:]:
            if isinstance(inner_dict, basestring):
                break
            if not any(inner_dict.values()):
                value.remove(inner_dict)
            else:
                clean_dict(inner_dict)
    return data_dict


def tuplize_dict(data_dict):
    '''Takes a dict with keys of the form 'table__0__key' and converts them
    to a tuple like ('table', 0, 'key').

    Dict should be put through parse_dict before this function, to have
    values standardized.

    May raise a DataError if the format of the key is incorrect.
    '''
    tuplized_dict = {}
    for key, value in data_dict.iteritems():
        key_list = key.split('__')
        for num, key in enumerate(key_list):
            if num % 2 == 1:
                try:
                    key_list[num] = int(key)
                except ValueError:
                    raise df.DataError('Bad key')
        tuplized_dict[tuple(key_list)] = value
    return tuplized_dict


def untuplize_dict(tuplized_dict):

    data_dict = {}
    for key, value in tuplized_dict.iteritems():
        new_key = '__'.join([str(item) for item in key])
        data_dict[new_key] = value
    return data_dict


def flatten_to_string_key(dict):

    flattented = df.flatten_dict(dict)
    return untuplize_dict(flattented)


def check_access(action, context, data_dict=None):
    user = context.get('user')

    log.debug('check access - user %r, action %s' % (user, action))

    if action:
        #if action != model.Action.READ and user in
        # (model.PSEUDO_USER__VISITOR, ''):
        #    # TODO Check the API key is valid at some point too!
        #    log.debug('Valid API key needed to make changes')
        #    raise NotAuthorized
        logic_authorization = new_authz.is_authorized(action, context, data_dict)
        if not logic_authorization['success']:
            msg = logic_authorization.get('msg', '')
            raise NotAuthorized(msg)
    elif not user:
        msg = _('No valid API key provided.')
        log.debug(msg)
        raise NotAuthorized(msg)

    log.debug('Access OK.')
    return True


_actions = {}
def clear_actions_cache():
    _actions.clear()

def get_action(action):
    '''Return the ckan.logic.action function named by the given string.

    For example:

        get_action('package_create')

    will normally return the ckan.logic.action.create.py:package_create()
    function.

    Rather than importing a ckan.logic.action function and calling it directly,
    you should always fetch the function via get_action():

        # Call the package_create action function:
        get_action('package_create')(context, data_dict)

    This is because CKAN plugins can override action functions using the
    IActions plugin interface, causing get_action() to return a plugin-provided
    function instead of the default one.

    As the context parameter passed to an action function is commonly:

        context = {'model': ckan.model, 'session': ckan.model.Session,
                   'user': pylons.c.user or pylons.c.author}

    an action function returned by get_action() will automatically add these
    parameters to the context if they are not defined.  This is especially
    useful for extensions as they should not really be importing parts of ckan
    eg ckan.model and as such do not have access to model or model.Session.

    If a context of None is passed to the action function then the context dict
    will be created.

    :param action: name of the action function to return
    :type action: string

    :returns: the named action function
    :rtype: callable

    '''

    # clean the action names
    action = new_authz.clean_action_name(action)

    if _actions:
        if not action in _actions:
            raise KeyError("Action '%s' not found" % action)
        return _actions.get(action)
    # Otherwise look in all the plugins to resolve all possible
    # First get the default ones in the ckan/logic/action directory
    # Rather than writing them out in full will use __import__
    # to load anything from ckan.logic.action that looks like it might
    # be an action
    for action_module_name in ['get', 'create', 'update', 'delete']:
        module_path = 'ckan.logic.action.' + action_module_name
        module = __import__(module_path)
        for part in module_path.split('.')[1:]:
            module = getattr(module, part)
        for k, v in module.__dict__.items():
            if not k.startswith('_'):
                # Only load functions from the action module.
                if isinstance(v, types.FunctionType):
                    k = new_authz.clean_action_name(k)
                    _actions[k] = v

                    # Whitelist all actions defined in logic/action/get.py as
                    # being side-effect free.
                    v.side_effect_free = getattr(v, 'side_effect_free', True)\
                        and action_module_name == 'get'

    # Then overwrite them with any specific ones in the plugins:
    resolved_action_plugins = {}
    fetched_actions = {}
    for plugin in p.PluginImplementations(p.IActions):
        for name, auth_function in plugin.get_actions().items():
            name = new_authz.clean_action_name(name)
            if name in resolved_action_plugins:
                raise Exception(
                    'The action %r is already implemented in %r' % (
                        name,
                        resolved_action_plugins[name]
                    )
                )
            log.debug('Auth function %r was inserted', plugin.name)
            resolved_action_plugins[name] = plugin.name
            fetched_actions[name] = auth_function
    # Use the updated ones in preference to the originals.
    _actions.update(fetched_actions)

    # wrap the functions
    for action_name, _action in _actions.items():
        def make_wrapped(_action, action_name):
            def wrapped(context=None, data_dict=None, **kw):
                if kw:
                    log.critical('%s was pass extra keywords %r'
                                 % (_action.__name__, kw))
                if context is None:
                    context = {}
                context.setdefault('model', model)
                context.setdefault('session', model.Session)
                try:
                    context.setdefault('user', c.user or c.author)
                except TypeError:
                    # c not registered
                    pass
                return _action(context, data_dict, **kw)
            return wrapped

        fn = make_wrapped(_action, action_name)
        # we need to mirror the docstring
        fn.__doc__ = _action.__doc__
        # we need to retain the side effect free behaviour
        if getattr(_action, 'side_effect_free', False):
            fn.side_effect_free = True
        _actions[action_name] = fn

    return _actions.get(action)


def get_or_bust(data_dict, keys):
    '''Try and get values from dictionary and if they are not there
    raise a validation error.

    data_dict: a dictionary
    keys: either a single string key in which case will return a single value,
    or a iterable which will return a tuple for unpacking purposes.

    e.g single_value = get_or_bust(data_dict, 'a_key')
        value_1, value_2 = get_or_bust(data_dict, ['key1', 'key2'])
    '''

    if isinstance(keys, basestring):
        keys = [keys]

    import ckan.logic.schema as schema
    schema = schema.create_schema_for_required_keys(keys)

    data_dict, errors = _validate(data_dict, schema)

    if errors:
        raise ValidationError(errors)

    # preserve original key order
    values = [data_dict[key] for key in keys]
    if len(values) == 1:
        return values[0]
    return tuple(values)


def side_effect_free(action):
    '''A decorator that marks the given action as side-effect-free.

    The consequence of which is that the action becomes available through a
    GET request in the action API.

    This decorator is for users defining their own actions through the IAction
    interface, and they want to expose their action with a GET request as well
    as the usual POST request.
    '''

    @functools.wraps(action)
    def wrapper(context, data_dict):
        return action(context, data_dict)
    wrapper.side_effect_free = True

    return wrapper


def auth_sysadmins_check(action):
    ''' Prevent sysadmins from automatically being authenticated.  Instead
    they are treated like any other user and the auth function is called.
    '''
    @functools.wraps(action)
    def wrapper(context, data_dict):
        return action(context, data_dict)
    wrapper.auth_sysadmins_check = True
    return wrapper



class UnknownValidator(Exception):
    pass


_validators_cache = {}

def clear_validators_cache():
    _validators_cache.clear()


def get_validator(validator):
    '''Return a validator by name or UnknownValidator exception if the
    validator is not found.  This is mainly so that validators can be made
    available to extensions via the plugin toolkit.

    :param validator: name of the validator requested
    :type validator: string
    '''
    if  not _validators_cache:
        validators = _import_module_functions('ckan.lib.navl.validators')
        _validators_cache.update(validators)
        validators = _import_module_functions('ckan.logic.validators')
        _validators_cache.update(validators)
        _validators_cache.update({'OneOf': formencode.validators.OneOf})
    try:
        return _validators_cache[validator]
    except KeyError:
        raise UnknownValidator('Validator `%s` does not exist' % validator)


class UnknownConverter(Exception):
    pass


_converters_cache = {}

def clear_converters_cache():
    _converters_cache.clear()


def get_converter(converter):
    '''Return a converter by name or UnknownConverter exception if the
    converter is not found.  This is mainly so that validators can be made
    available to extensions via the plugin toolkit.

    :param converter: name of the converter requested
    :type converter: string
    '''
    if not _converters_cache:
        converters = _import_module_functions('ckan.logic.converters')
        _converters_cache.update(converters)
    try:
        return _converters_cache[converter]
    except KeyError:
        raise UnknownConverter('Converter `%s` does not exist' % converter)


def model_name_to_class(model_module, model_name):
    '''Return the class in model_module that has the same name as the received string.

    Raises AttributeError if there's no model in model_module named model_name.
    '''
    try:
        model_class_name = model_name.title()
        return getattr(model_module, model_class_name)
    except AttributeError:
        raise ValidationError("%s isn't a valid model" % model_class_name)

def _import_module_functions(module_path):
    '''Import a module and get the functions and return them in a dict'''
    functions_dict = {}
    module = __import__(module_path)
    for part in module_path.split('.')[1:]:
        module = getattr(module, part)
    for k, v in module.__dict__.items():

        try:
            if v.__module__ != module_path:
                continue
            functions_dict[k] = v
        except AttributeError:
            pass
    return functions_dict
