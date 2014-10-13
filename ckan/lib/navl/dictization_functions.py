import copy
import formencode as fe
import inspect
import json
from pylons import config

from ckan.common import _

class Missing(object):
    def __unicode__(self):
        raise Invalid(_('Missing value'))
    def __str__(self):
        raise Invalid(_('Missing value'))
    def __int__(self):
        raise Invalid(_('Missing value'))
    def __complex__(self):
        raise Invalid(_('Missing value'))
    def __long__(self):
        raise Invalid(_('Missing value'))
    def __float__(self):
        raise Invalid(_('Missing value'))
    def __oct__(self):
        raise Invalid(_('Missing value'))
    def __hex__(self):
        raise Invalid(_('Missing value'))
    def __nonzero__(self):
        return False

missing = Missing()

class State(object):
    pass

class DictizationError(Exception):
    def __str__(self):
        if hasattr(self, 'error') and self.error:
            return repr(self.error)
        return ''

class Invalid(DictizationError):
    '''Exception raised by some validator, converter and dictization functions
    when the given value is invalid.

    '''
    def __init__(self, error, key=None):
        self.error = error

class DataError(DictizationError):
    def __init__(self, error):
        self.error = error

class StopOnError(DictizationError):
    '''error to stop validations for a particualar key'''
    pass

def flattened_order_key(key):
    '''order by key length first then values'''

    return tuple([len(key)] + list(key))

def flatten_schema(schema, flattened=None, key=None):
    '''convert schema into flat dict where the keys are tuples'''

    flattened = flattened or {}
    old_key = key or []

    for key, value in schema.iteritems():
        new_key = old_key + [key]
        if isinstance(value, dict):
            flattened = flatten_schema(value, flattened, new_key)
        else:
            flattened[tuple(new_key)] = value

    return flattened

def get_all_key_combinations(data, flattented_schema):
    '''Compare the schema against the given data and get all valid tuples that
    match the schema ignoring the last value in the tuple.

    '''
    schema_prefixes = set([key[:-1] for key in flattented_schema])
    combinations = set([()])

    for key in sorted(data.keys(), key=flattened_order_key):
        ## make sure the tuple key is a valid one in the schema
        key_prefix = key[:-1:2]
        if key_prefix not in schema_prefixes:
            continue
        ## make sure the parent key exists, this is assured by sorting the keys
        ## first
        if tuple(tuple(key[:-3])) not in combinations:
            continue
        combinations.add(tuple(key[:-1]))

    return combinations

def make_full_schema(data, schema):
    '''make schema by getting all valid combinations and making sure that all keys
    are available'''

    flattented_schema = flatten_schema(schema)

    key_combinations = get_all_key_combinations(data, flattented_schema)

    full_schema = {}

    for combination in key_combinations:
        sub_schema = schema
        for key in combination[::2]:
            sub_schema = sub_schema[key]

        for key, value in sub_schema.iteritems():
            if isinstance(value, list):
                full_schema[combination + (key,)] = value

    return full_schema

def augment_data(data, schema):
    '''add missing, extras and junk data'''
    flattented_schema = flatten_schema(schema)
    key_combinations = get_all_key_combinations(data, flattented_schema)

    full_schema = make_full_schema(data, schema)

    new_data = copy.copy(data)

    ## fill junk and extras

    for key, value in new_data.items():
        if key in full_schema:
            continue

        ## check if any thing naugthy is placed against subschemas
        initial_tuple = key[::2]
        if initial_tuple in [initial_key[:len(initial_tuple)]
                             for initial_key in flattented_schema]:
            if data[key] <> []:
                raise DataError('Only lists of dicts can be placed against '
                                'subschema %s, not %s' % (key,type(data[key])))

        if key[:-1] in key_combinations:
            extras_key = key[:-1] + ('__extras',)
            extras = new_data.get(extras_key, {})
            extras[key[-1]] = value
            new_data[extras_key] = extras
        else:
            junk = new_data.get(("__junk",), {})
            junk[key] = value
            new_data[("__junk",)] = junk
        new_data.pop(key)

    ## add missing

    for key, value in full_schema.items():
        if key not in new_data and not key[-1].startswith("__"):
            new_data[key] = missing

    return new_data

def convert(converter, key, converted_data, errors, context):

    if inspect.isclass(converter) and issubclass(converter, fe.Validator):
        try:
            value = converted_data.get(key)
            value = converter().to_python(value, state=context)
        except fe.Invalid, e:
            errors[key].append(e.msg)
        return

    if isinstance(converter, fe.Validator):
        try:
            value = converted_data.get(key)
            value = converter.to_python(value, state=context)
        except fe.Invalid, e:
            errors[key].append(e.msg)
        return

    try:
        value = converter(converted_data.get(key))
        converted_data[key] = value
        return
    except TypeError, e:
        ## hack to make sure the type error was caused by the wrong
        ## number of arguments given.
        if not converter.__name__ in str(e):
            raise
    except Invalid, e:
        errors[key].append(e.error)
        return

    try:
        converter(key, converted_data, errors, context)
        return
    except Invalid, e:
        errors[key].append(e.error)
        return
    except TypeError, e:
        ## hack to make sure the type error was caused by the wrong
        ## number of arguments given.
        if not converter.__name__ in str(e):
            raise

    try:
        value = converter(converted_data.get(key), context)
        converted_data[key] = value
        return
    except Invalid, e:
        errors[key].append(e.error)
        return

def _remove_blank_keys(schema):

    for key, value in schema.items():
        if isinstance(value[0], dict):
            for item in value:
                _remove_blank_keys(item)
            if not any(value):
                schema.pop(key)

    return schema

def validate(data, schema, context=None):
    '''Validate an unflattened nested dict against a schema.'''
    context = context or {}

    assert isinstance(data, dict)

    # store any empty lists in the data as they will get stripped out by
    # the _validate function. We do this so we can differentiate between
    # empty fields and missing fields when doing partial updates.
    empty_lists = [key for key, value in data.items() if value == []]

    flattened = flatten_dict(data)
    converted_data, errors = _validate(flattened, schema, context)
    converted_data = unflatten(converted_data)

    # check config for partial update fix option
    if config.get('ckan.fix_partial_updates', True):
        # repopulate the empty lists
        for key in empty_lists:
            if key not in converted_data:
                converted_data[key] = []

    errors_unflattened = unflatten(errors)

    ##remove validators that passed
    dicts_to_process = [errors_unflattened]
    while dicts_to_process:
        dict_to_process = dicts_to_process.pop()
        for key, value in dict_to_process.items():
            if not value:
                dict_to_process.pop(key)
                continue
            if isinstance(value[0], dict):
                dicts_to_process.extend(value)

    _remove_blank_keys(errors_unflattened)

    return converted_data, errors_unflattened

def validate_flattened(data, schema, context=None):

    context = context or {}
    assert isinstance(data, dict)
    converted_data, errors = _validate(data, schema, context)

    for key, value in errors.items():
        if not value:
            errors.pop(key)

    return converted_data, errors


def _validate(data, schema, context):
    '''validate a flattened dict against a schema'''
    converted_data = augment_data(data, schema)
    full_schema = make_full_schema(data, schema)

    errors = dict((key, []) for key in full_schema)

    ## before run
    for key in sorted(full_schema, key=flattened_order_key):
        if key[-1] == '__before':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    ## main run
    for key in sorted(full_schema, key=flattened_order_key):
        if not key[-1].startswith('__'):
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    ## extras run
    for key in sorted(full_schema, key=flattened_order_key):
        if key[-1] == '__extras':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    ## after run
    for key in reversed(sorted(full_schema, key=flattened_order_key)):
        if key[-1] == '__after':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    ## junk
    if ('__junk',) in full_schema:
        for converter in full_schema[('__junk',)]:
            try:
                convert(converter, ('__junk',), converted_data, errors, context)
            except StopOnError:
                break

    return converted_data, errors


def flatten_list(data, flattened=None, old_key=None):
    '''flatten a list of dicts'''

    flattened = flattened or {}
    old_key = old_key or []

    for num, value in enumerate(data):
        if not isinstance(value, dict):
            raise DataError('Values in lists need to be dicts')
        new_key = old_key + [num]
        flattened = flatten_dict(value, flattened, new_key)

    return flattened

def flatten_dict(data, flattened=None, old_key=None):
    '''flatten a dict'''

    flattened = flattened or {}
    old_key = old_key or []

    for key, value in data.iteritems():
        new_key = old_key + [key]
        if isinstance(value, list) and value and isinstance(value[0], dict):
            flattened = flatten_list(value, flattened, new_key)
        else:
            flattened[tuple(new_key)] = value

    return flattened


def unflatten(data):
    '''Unflatten a simple dict whose keys are tuples.

    e.g.
    >>> unflatten(
      {('name',): u'testgrp4',
       ('title',): u'',
       ('description',): u'',
       ('packages', 0, 'name'): u'testpkg',
       ('packages', 1, 'name'): u'testpkg',
       ('extras', 0, 'key'): u'packages',
       ('extras', 0, 'value'): u'["testpkg"]',
       ('extras', 1, 'key'): u'',
       ('extras', 1, 'value'): u'',
       ('state',): u'active'
       ('save',): u'Save Changes',
       ('cancel',): u'Cancel'})
    {'name': u'testgrp4',
     'title': u'',
     'description': u'',
     'packages': [{'name': u'testpkg'}, {'name': u'testpkg'}],
     'extras': [{'key': u'packages', 'value': u'["testpkg"]'},
                {'key': u'', 'value': u''}],
     'state': u'active',
     'save': u'Save Changes',
     'cancel': u'Cancel'}
    '''

    unflattened = {}
    convert_to_list = []

    for flattend_key in sorted(data.keys(), key=flattened_order_key):
        current_pos = unflattened

        if (len(flattend_key) > 1
            and not flattend_key[0] in convert_to_list
            and not flattend_key[0] in unflattened):
            convert_to_list.append(flattend_key[0])

        for key in flattend_key[:-1]:
            try:
                current_pos = current_pos[key]
            except KeyError:
                new_pos = {}
                current_pos[key] = new_pos
                current_pos = new_pos
        current_pos[flattend_key[-1]] = data[flattend_key]

    for key in convert_to_list:
        unflattened[key] = [unflattened[key][s] for s in sorted(unflattened[key])]

    return unflattened


class MissingNullEncoder(json.JSONEncoder):
    '''json encoder that treats missing objects as null'''
    def default(self, obj):
        if isinstance(obj, Missing):
            return None
        return json.JSONEncoder.default(self, obj)
