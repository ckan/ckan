# encoding: utf-8

from ckan.lib.navl.dictization_functions import (flatten_schema,
                                   get_all_key_combinations,
                                   make_full_schema,
                                   flatten_dict,
                                   unflatten,
                                   missing,
                                   augment_data,
                                   validate,
                                   _validate)
from pprint import pprint, pformat
from ckan.lib.navl.validators import (identity_converter,
                        empty,
                        not_empty,
                        ignore_missing,
                        default,
                        convert_int,
                        ignore)

from formencode import validators


schema = {
    "__after": [identity_converter],
    "__extra": [identity_converter],
    "__junk": [identity_converter],
    "0": [identity_converter],
    "1": [identity_converter],
    "2": {
        "__before": [identity_converter],
        "__after": [identity_converter],
        "20": [identity_converter],
        "22": [identity_converter],
        "21": {
            "210": [identity_converter],
        },
    },
    "3": {
        "30": [identity_converter],
    }
}

data = {
    ("0",): "0 value",
    #key 1 missing
    ("2", 0, "20"): "20 value 0",
    #key 2,22 missing
    ("2", 0, "21", 0, "210"): "210 value 0,0",
    #key 3 missing subdict
    ("2", 1, "20"): "20 value 1",
    ("2", 1, "22"): "22 value 1",
    ("2", 1, "21", 0, "210"): "210 value 1,0",
    ("2", 1, "21", 1, "210"): "210 value 1,1",
    ("2", 1, "21", 3, "210"): "210 value 1,3", ##out of order sequence
    ("4", 1, "30"): "30 value 1", #junk key as no 4 and no subdict
    ("4",): "4 value", #extra key 4
#    ("2", 2, "21", 0, "210"): "210 value 2,0" #junk key as it does not have a parent
}


def test_flatten_schema():

    flattened_schema = flatten_schema(schema)

    assert flattened_schema == {
         ('0',): [identity_converter],
         ('1',): [identity_converter],
         ('2', '20'): [identity_converter],
         ('2', '__after'): [identity_converter],
         ('2', '__before'): [identity_converter],
         ('2', '21', '210'): [identity_converter],
         ('2', '22'): [identity_converter],
         ('3', '30'): [identity_converter],
         ('__after',): [identity_converter],
         ('__extra',): [identity_converter],
         ('__junk',): [identity_converter],
    }, pprint(flattened_schema)

def test_get_key_combination():

    flattened_schema = flatten_schema(schema)
    assert get_all_key_combinations(data, flattened_schema) ==\
        set([(),
            ('2', 0), 
            ('2', 1), 
            ('2', 1, '21', 0),
            ('2', 0, '21', 0),
            ('2', 1, '21', 1), 
            ('2', 1, '21', 3), 
            ]), get_all_key_combinations(data, flattened_schema)

    #state = {}
    #make_flattened_schema(data, schema, state)

def test_make_full_schema():

    full_schema = make_full_schema(data, schema)

    print set(full_schema.keys()) - set(data.keys())

    assert set(full_schema.keys()) - set(data.keys()) == set([('2', 1, '__before'),
                                                              ('2', 0, '__after'),
                                                              ('2', 0, '22'),
                                                              ('1',),
                                                              ('2', 1, '__after'),
                                                              ('2', 0, '__before'),
                                                              ('__after',),
                                                              ('__extra',),
                                                              ('__junk',),
                                                             ])

    print set(data.keys()) - set(full_schema.keys())

    assert set(data.keys()) - set(full_schema.keys()) == set([('4',),
                                                              ('4', 1, '30')])


def test_augment_junk_and_extras():

    assert augment_data(data, schema) == {
         ('__junk',): {('4', 1, '30'): '30 value 1'},
         ('0',): '0 value',
         ('1',): missing,
         ('2', 0, '20'): '20 value 0',
         ('2', 0, '21', 0, '210'): '210 value 0,0',
         ('2', 0, '22'): missing,
         ('2', 1, '20'): '20 value 1',
         ('2', 1, '21', 0, '210'): '210 value 1,0',
         ('2', 1, '21', 1, '210'): '210 value 1,1',
         ('2', 1, '21', 3, '210'): '210 value 1,3',
         ('2', 1, '22'): '22 value 1',
         ('__extras',): {'4': '4 value'}}, pprint(augment_data(data, schema))


def test_identity_validation():

    
    converted_data, errors = validate_flattened(data, schema)
    print errors
    print converted_data

    assert not errors


    assert sorted(converted_data) == sorted({
         ('__junk',): {('2', 2, '21', 0, '210'): '210 value 2,0',
                       ('4', 1, '30'): '30 value 1'},
         ('0',): '0 value',
         ('1',): missing,
         ('2', 0, '20'): '20 value 0',
         ('2', 0, '21', 0, '210'): '210 value 0,0',
         ('2', 0, '22'): missing,
         ('2', 1, '20'): '20 value 1',
         ('2', 1, '21', 0, '210'): '210 value 1,0',
         ('2', 1, '21', 1, '210'): '210 value 1,1',
         ('2', 1, '21', 3, '210'): '210 value 1,3',
         ('2', 1, '22'): '22 value 1',
         ('__extras',): {'4': '4 value'}}), pformat(sorted(converted_data))


def test_basic_errors():
    schema = {
        "__junk": [empty],
        "__extras": [empty],
        "0": [identity_converter],
        "1": [not_empty],
        "2": {
            "__before": [identity_converter],
            "__after": [identity_converter],
            "20": [identity_converter],
            "22": [identity_converter],
            "__extras": [empty],
            "21": {
                "210": [identity_converter],
            },
        },
        "3": {
            "30": [identity_converter],
        },
    }

    converted_data, errors = validate_flattened(data, schema)

    assert errors == {('__junk',): [u"The input field [('4', 1, '30')] was not expected."], ('1',): [u'Missing value'], ('__extras',): [u'The input field __extras was not expected.']}, errors

def test_default():
    schema = {
        "__junk": [ignore],
        "__extras": [ignore, default("weee")],
        "__before": [ignore],
        "__after": [ignore],
        "0": [default("default")],
        "1": [default("default")],
    }

    converted_data, errors = validate_flattened(data, schema)

    assert not errors
    assert converted_data == {('1',): 'default', ('0',): '0 value'}, converted_data


def test_flatten():

    data = {'extras': [{'key': 'genre', 'value': u'horror'},
                       {'key': 'media', 'value': u'dvd'}],
            'license_id': u'gpl-3.0',
            'name': u'testpkg',
            'resources': [{u'alt_url': u'alt_url',
                          u'description': u'Second file',
                          u'extras': {u'size': u'200'},
                          u'format': u'xml',
                          u'hash': u'def123',
                          u'url': u'http://blah.com/file2.xml'},
                          {u'alt_url': u'alt_url',
                          u'description': u'Main file',
                          u'extras': {u'size': u'200'},
                          u'format': u'xml',
                          u'hash': u'abc123',
                          u'url': u'http://blah.com/file.xml'}],
            'tags': [{'name': u'russion'}, {'name': u'novel'}],
            'title': u'Some Title',
            'url': u'http://blahblahblah.mydomain'}

    assert flatten_dict(data) == {('extras', 0, 'key'): 'genre',
                                 ('extras', 0, 'value'): u'horror',
                                 ('extras', 1, 'key'): 'media',
                                 ('extras', 1, 'value'): u'dvd',
                                 ('license_id',): u'gpl-3.0',
                                 ('name',): u'testpkg',
                                 ('resources', 0, u'alt_url'): u'alt_url',
                                 ('resources', 0, u'description'): u'Second file',
                                 ('resources', 0, u'extras'): {u'size': u'200'},
                                 ('resources', 0, u'format'): u'xml',
                                 ('resources', 0, u'hash'): u'def123',
                                 ('resources', 0, u'url'): u'http://blah.com/file2.xml',
                                 ('resources', 1, u'alt_url'): u'alt_url',
                                 ('resources', 1, u'description'): u'Main file',
                                 ('resources', 1, u'extras'): {u'size': u'200'},
                                 ('resources', 1, u'format'): u'xml',
                                 ('resources', 1, u'hash'): u'abc123',
                                 ('resources', 1, u'url'): u'http://blah.com/file.xml',
                                 ('tags', 0, 'name'): u'russion',
                                 ('tags', 1, 'name'): u'novel',
                                 ('title',): u'Some Title',
                                 ('url',): u'http://blahblahblah.mydomain'}, pformat(flatten_dict(data))

    assert data == unflatten(flatten_dict(data))


def test_simple():
    schema = {
        "name": [not_empty],
        "age": [ignore_missing, convert_int],
        "gender": [default("female")],
    }

    data = {
        "name": "fred",
        "age": "32",
    }


    converted_data, errors = validate(data, schema)

    assert not errors
    assert converted_data == {'gender': 'female', 'age': 32, 'name': 'fred'}, converted_data

    data = {
        "name": "",
        "age": "dsa32",
        "extra": "extra",
    }

    converted_data, errors = validate(data, schema)

    assert errors == {'age': [u'Please enter an integer value'], 'name': [u'Missing value']}, errors

    assert converted_data == {'gender': 'female', 'age': 'dsa32', 'name': '', '__extras': {'extra': 'extra'}}


    data = {"name": "fred",
            "numbers": [{"number": "13221312"},
                        {"number": "432423432", "code": "+44"}]
            }

    schema = {
           "name": [not_empty],
           "numbers": {
               "number": [convert_int],
               "code": [not_empty],
               "__extras": [ignore],
           }
        }

    converted_data, errors = validate(data, schema)

    print errors
    assert errors == {'numbers': [{'code': [u'Missing value']}, {}]}


def test_simple_converter_types():
    schema = {
        "name": [not_empty, unicode],
        "age": [ignore_missing, int],
        "gender": [default("female")],
    }

    data = {
        "name": "fred",
        "age": "32",
    }

    converted_data, errors = validate(data, schema)
    assert not errors
    assert converted_data == {'gender': 'female', 'age': 32, 'name': u'fred'}, converted_data

    assert isinstance(converted_data["name"], unicode)
    assert not isinstance(converted_data["gender"], unicode)


def test_formencode_compat():
    schema = {
        "name": [not_empty, unicode],
        "email": [validators.Email],
        "email2": [validators.Email],
    }

    data = {
        "name": "fred",
        "email": "32",
        "email2": "david@david.com",
    }

    converted_data, errors = validate(data, schema)
    assert errors == {'email': [u'An email address must contain a single @']}, errors

def test_range_validator():

    schema = {
        "name": [not_empty, unicode],
        "email": [validators.Int(min=1, max=10)],
        "email2": [validators.Email],
    }

    data = {
        "email": "32",
        "email2": "david@david.com",
    }

    converted_data, errors = validate(data, schema)
    assert errors == {'name': [u'Missing value'], 'email': [u'Please enter a number that is 10 or smaller']}, errors


def validate_flattened(data, schema, context=None):

    context = context or {}
    assert isinstance(data, dict)
    converted_data, errors = _validate(data, schema, context)

    for key, value in errors.items():
        if not value:
            errors.pop(key)

    return converted_data, errors
