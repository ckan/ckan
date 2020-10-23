# encoding: utf-8

import copy
import json

import six
from six import text_type
from ckan.common import config, _


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

    def __len__(self):
        return 0


missing = Missing()


class State(object):
    pass


class DictizationError(Exception):
    def __str__(self):
        return six.ensure_str(self.__unicode__())

    def __unicode__(self):
        if hasattr(self, 'error') and self.error:
            return u'{}: {}'.format(self.__class__.__name__, repr(self.error))
        return self.__class__.__name__

    def __repr__(self):
        if hasattr(self, 'error') and self.error:
            return '<{} {}>'.format(self.__class__.__name__, repr(self.error))
        return '<{}>'.format(self.__class__.__name__)


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
    '''convert schema into flat dict, where the keys become tuples

    e.g.
    {
      "toplevel": [validators],
      "parent": {
        "child1": [validators],
        "child2": [validators],
        }
    }
    becomes:
    {
      ('toplevel',): [validators],
      ('parent', 'child1'): [validators],
      ('parent', 'child2'): [validators],
    }
    See also: test_flatten_schema()
    '''
    flattened = flattened or {}
    old_key = key or []

    for key, value in six.iteritems(schema):
        new_key = old_key + [key]
        if isinstance(value, dict):
            flattened = flatten_schema(value, flattened, new_key)
        else:
            flattened[tuple(new_key)] = value

    return flattened


def get_all_key_combinations(data, flattened_schema):
    '''Compare the schema against the given data and get all valid tuples that
    match the schema ignoring the last value in the tuple.

    '''
    schema_prefixes = {key[:-1] for key in flattened_schema}
    combinations = set([()])

    for key in sorted(data.keys(), key=flattened_order_key):
        # make sure the tuple key is a valid one in the schema
        key_prefix = key[:-1:2]
        if key_prefix not in schema_prefixes:
            continue
        # make sure the parent key exists, this is assured by sorting the keys
        # first
        if tuple(tuple(key[:-3])) not in combinations:
            continue
        combinations.add(tuple(key[:-1]))

    return combinations


def make_full_schema(data, schema):
    '''make schema by getting all valid combinations and making sure that all
    keys are available'''

    flattened_schema = flatten_schema(schema)

    key_combinations = get_all_key_combinations(data, flattened_schema)

    full_schema = {}

    for combination in key_combinations:
        sub_schema = schema
        for key in combination[::2]:
            sub_schema = sub_schema[key]

        for key, value in six.iteritems(sub_schema):
            if isinstance(value, list):
                full_schema[combination + (key,)] = value

    return full_schema


def augment_data(data, schema):
    '''Takes 'flattened' data, compares it with the schema, and returns it with
    any problems marked, as follows:

    * keys in the data not in the schema are moved into a list under new key
      ('__junk')
    * keys in the schema but not data are added as keys with value 'missing'

    '''
    flattened_schema = flatten_schema(schema)
    key_combinations = get_all_key_combinations(data, flattened_schema)

    full_schema = make_full_schema(data, schema)

    new_data = copy.copy(data)

    keys_to_remove = []
    junk = {}
    extras_keys = {}
    # fill junk and extras
    for key, value in new_data.items():
        if key in full_schema:
            continue

        # check if any thing naughty is placed against subschemas
        initial_tuple = key[::2]
        if initial_tuple in [initial_key[:len(initial_tuple)]
                             for initial_key in flattened_schema]:
            if data[key] != []:
                raise DataError('Only lists of dicts can be placed against '
                                'subschema %s, not %s' %
                                (key, type(data[key])))
        if key[:-1] in key_combinations:
            extras_key = key[:-1] + ('__extras',)
            extras = extras_keys.get(extras_key, {})
            extras[key[-1]] = value
            extras_keys[extras_key] = extras
        else:
            junk[key] = value
        keys_to_remove.append(key)

    if junk:
        new_data[("__junk",)] = junk
    for extra_key in extras_keys:
        new_data[extra_key] = extras_keys[extra_key]

    for key in keys_to_remove:
        new_data.pop(key)

    # add missing

    for key, value in full_schema.items():
        if key not in new_data and not key[-1].startswith("__"):
            new_data[key] = missing

    return new_data


def convert(converter, key, converted_data, errors, context):

    try:
        value = converter(converted_data.get(key))
        converted_data[key] = value
        return
    except TypeError as e:
        # hack to make sure the type error was caused by the wrong
        # number of arguments given.
        if converter.__name__ not in str(e):
            raise
    except Invalid as e:
        errors[key].append(e.error)
        return

    try:
        converter(key, converted_data, errors, context)
        return
    except Invalid as e:
        errors[key].append(e.error)
        return
    except TypeError as e:
        # hack to make sure the type error was caused by the wrong
        # number of arguments given.
        if converter.__name__ not in str(e):
            raise

    try:
        value = converter(converted_data.get(key), context)
        converted_data[key] = value
        return
    except Invalid as e:
        errors[key].append(e.error)
        return


def validate(data, schema, context=None):
    '''Validate an unflattened nested dict against a schema.'''
    context = context or {}

    assert isinstance(data, dict)

    # store any empty lists in the data as they will get stripped out by
    # the _validate function. We do this so we can differentiate between
    # empty fields and missing fields when doing partial updates.
    empty_lists = [key for key, value in data.items() if value == []]

    # create a copy of the context which also includes the schema keys so
    # they can be used by the validators
    validators_context = dict(context, schema_keys=list(schema.keys()))

    flattened = flatten_dict(data)
    converted_data, errors = _validate(flattened, schema, validators_context)
    converted_data = unflatten(converted_data)

    # check config for partial update fix option
    if config.get('ckan.fix_partial_updates', True):
        # repopulate the empty lists
        for key in empty_lists:
            if key not in converted_data:
                converted_data[key] = []

    # remove validators that passed
    for key in list(errors.keys()):
        if not errors[key]:
            del errors[key]

    errors_unflattened = unflatten(errors)

    return converted_data, errors_unflattened


def _validate(data, schema, context):
    '''validate a flattened dict against a schema'''
    converted_data = augment_data(data, schema)
    full_schema = make_full_schema(data, schema)

    errors = dict((key, []) for key in full_schema)

    # before run
    for key in sorted(full_schema, key=flattened_order_key):
        if key[-1] == '__before':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    # main run
    for key in sorted(full_schema, key=flattened_order_key):
        if not key[-1].startswith('__'):
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    # extras run
    for key in sorted(full_schema, key=flattened_order_key):
        if key[-1] == '__extras':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    # after run
    for key in reversed(sorted(full_schema, key=flattened_order_key)):
        if key[-1] == '__after':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    # junk
    if ('__junk',) in full_schema:
        for converter in full_schema[('__junk',)]:
            try:
                convert(converter, ('__junk',), converted_data, errors,
                        context)
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
    '''Flatten a dict'''

    flattened = flattened or {}
    old_key = old_key or []

    for key, value in six.iteritems(data):
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
    clean_lists = {}

    for flattend_key in sorted(data.keys(), key=flattened_order_key):
        current_pos = unflattened

        for key in flattend_key[:-1]:
            try:
                current_pos = current_pos[key]
            except IndexError:
                while True:
                    new_pos = {}
                    current_pos.append(new_pos)
                    if key < len(current_pos):
                        break
                    # skipped list indexes need to be removed before returning
                    clean_lists[id(current_pos)] = current_pos
                current_pos = new_pos
            except KeyError:
                new_pos = []
                current_pos[key] = new_pos
                current_pos = new_pos
        current_pos[flattend_key[-1]] = data[flattend_key]

    for cl in clean_lists.values():
        cl[:] = [i for i in cl if i]

    return unflattened


class MissingNullEncoder(json.JSONEncoder):
    '''json encoder that treats missing objects as null'''
    def default(self, obj):
        if isinstance(obj, Missing):
            return None
        return json.JSONEncoder.default(self, obj)


def check_dict(data_dict, select_dict, parent_path=()):
    """
    return list of key tuples from select_dict whose values don't match
    corresponding values in data_dict.
    """
    if not isinstance(data_dict, dict):
        return [parent_path]

    unmatched = []
    for k, v in sorted(select_dict.items()):
        if k not in data_dict:
            unmatched.append(parent_path + (k,))

        elif isinstance(v, dict):
            unmatched.extend(check_dict(data_dict[k], v, parent_path + (k,)))

        elif isinstance(v, list):
            unmatched.extend(check_list(data_dict[k], v, parent_path + (k,)))

        elif data_dict[k] != v:
            unmatched.append(parent_path + (k,))

    return unmatched


def check_list(data_list, select_list, parent_path=()):
    """
    return list of key tuples from select_list whose values don't match
    corresponding values in data_list.
    """
    if not isinstance(data_list, list):
        return [parent_path]

    unmatched = []
    for i, v in enumerate(select_list):
        if i >= len(data_list):
            unmatched.append(parent_path + (i,))

        elif isinstance(v, dict):
            unmatched.extend(check_dict(data_list[i], v, parent_path + (i,)))

        elif isinstance(v, list):
            unmatched.extend(check_list(data_list[i], v, parent_path + (i,)))

        elif data_list[i] != v:
            unmatched.append(parent_path + (i,))

    return unmatched


def resolve_string_key(data, string_key):
    """
    return (child, parent_path) if string_key is found in data
    raise DataError on incompatible types or key not found.

    supports partial-id keys for lists of dicts (minimum 5 hex digits)
    e.g. `resources__1492a` would select the first matching resource
    with an id field matching "1492a..."
    """
    parent_path = []
    current = data
    for k in string_key.split('__'):
        if isinstance(current, dict):
            if k not in current:
                raise DataError('Unmatched key %s' % '__'.join(
                    str(p) for p in parent_path + [k]))
            parent_path.append(k)
            current = current[k]
            continue

        if not isinstance(current, list):
            raise DataError('Unmatched key %s' % '__'.join(
                str(p) for p in parent_path + [k]))

        if len(k) >= 5:
            for i, rec in enumerate(current):
                if not isinstance(rec, dict) or 'id' not in rec:
                    raise DataError('Unmatched key %s' % '__'.join(
                        str(p) for p in parent_path + [k]))
                if rec['id'].startswith(k):
                    parent_path.append(i)
                    current = rec
                    break
            else:
                raise DataError('Unmatched key %s' % '__'.join(
                    str(p) for p in parent_path + [k]))
            continue

        try:
            index = int(k)
            if index < -len(current) or index >= len(current):
                raise ValueError
        except ValueError:
            raise DataError('Unmatched key %s' % '__'.join(
                str(p) for p in parent_path + [k]))

        parent_path.append(index)
        current = current[index]

    return current, tuple(parent_path)


def check_string_key(data_dict, string_key, value):
    """
    return list of key tuples from string_key whose values don't match
    corresponding values in data_dict.

    raise DataError on incompatible types such as checking for dict values
    in a list value.
    """
    current, parent_path = resolve_string_key(data_dict, string_key)
    if isinstance(value, dict):
        return check_dict(current, value, parent_path)
    if isinstance(value, list):
        return check_list(current, value, parent_path)
    if current != value:
        return [parent_path]
    return []


def filter_glob_match(data_dict, glob_patterns):
    """
    remove keys and values from data_dict in-place based on glob patterns.

    glob patterns are string_keys with optional '*' keys matching everything
    at that level. a '+' prefix on the glob pattern indicates values to
    protect from deletion, where the first matching pattern "wins".
    """
    return _filter_glob_match(data_dict, [
        (p.startswith('+'), p.lstrip('-+').split('__'))
        for p in glob_patterns])


def _filter_glob_match(data, parsed_globs):
    if isinstance(data, dict):
        protected = {}
        children = {}
        for keep, globs in parsed_globs:
            head = globs[0]
            if head == '*':
                if keep:
                    protected.update(data)
                else:
                    data.clear()
                continue
            if head not in data:
                continue

            if len(globs) > 1:
                children.setdefault(head, []).append((keep, globs[1:]))
            elif keep:
                protected[head] = data[head]
            else:
                del data[head]
        data.update(protected)

        for head in children:
            if head not in data:
                continue
            _filter_glob_match(data[head], children[head])

        return

    elif not isinstance(data, list):
        return

    protected = set()
    removed = set()
    children = {}
    for keep, globs in parsed_globs:
        head = globs[0]
        if head == '*':
            if keep:
                protected.update(set(range(len(data))) - removed)
            else:
                removed.update(set(range(len(data))) - protected)
            continue
        try:
            child, (index,) = resolve_string_key(data, head)
        except DataError:
            continue

        if len(globs) > 1:
            children.setdefault(index, []).append((keep, globs[1:]))
        elif keep:
            if index not in removed:
                protected.add(index)
        else:
            if index not in protected:
                removed.add(index)

        for head in children:
            if head not in removed - protected:
                _filter_glob_match(data[head], children[head])

    data[:] = [e for i, e in enumerate(data) if i not in removed - protected]


def update_merge_dict(data_dict, update_dict, parent_path=()):
    """
    update data_dict keys and values in-place based on update_dict.

    raise DataError on incompatible types such as replacing a dict with a list
    """
    if not isinstance(update_dict, dict):
        raise DataError('Expected dict for %s' % '__'.join(
            str(p) for p in parent_path))

    for k, v in update_dict.items():
        if k not in data_dict:
            data_dict[k] = v
        elif isinstance(data_dict[k], dict):
            update_merge_dict(data_dict[k], v, parent_path + (k,))
        elif isinstance(data_dict[k], list):
            update_merge_list(data_dict[k], v, parent_path + (k,))
        else:
            data_dict[k] = v


def update_merge_list(data_list, update_list, parent_path=()):
    """
    update data_list entries in-place based on update_list.

    raise DataError on incompatible types such as replacing a dict with a list
    """
    if not isinstance(update_list, list):
        raise DataError('Expected list for %s' % '__'.join(
            str(p) for p in parent_path))

    for i, v in enumerate(update_list):
        if i >= len(data_list):
            data_list.append(v)
        elif isinstance(data_list[i], dict):
            update_merge_dict(data_list[i], v, parent_path + (i,))
        elif isinstance(data_list[i], list):
            update_merge_list(data_list[i], v, parent_path + (i,))
        else:
            data_list[i] = v


def update_merge_string_key(data_dict, string_key, value):
    """
    update data_dict entries in-place based on string_key and value.
    Also supports extending existing lists with `__extend` suffix.

    raise DataError on incompatible types such as replacing a dict with a list
    """

    parts = string_key.split('__')
    k = parts[-1]
    string_key = '__'.join(parts[:-1])

    if string_key:
        current, parent_path = resolve_string_key(data_dict, string_key)
    else:
        current = data_dict
        parent_path = ()

    if isinstance(current, dict):
        update_merge_dict(current, {k: value}, parent_path)
    elif isinstance(current, list):
        if k == 'extend':
            if not isinstance(value, list):
                raise DataError('Expected list for %s' % string_key)
            current.extend(value)
            return

        child, (index,) = resolve_string_key(current, k)
        if isinstance(child, dict):
            update_merge_dict(child, value, parent_path + (index,))
        elif isinstance(child, list):
            update_merge_list(child, value, parent_path + (index,))
        else:
            current[index] = value
    else:
        raise DataError('Expected list or dict for %s' % string_key)
