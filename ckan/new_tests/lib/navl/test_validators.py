# -*- coding: utf-8 -*-
'''Unit tests for ckan/lib/navl/validators.py.

'''
import copy

import nose.tools


def _data():
    '''Return a data dict with some arbitrary data in it, suitable to be passed
    to validators for testing.

    This is a function that returns a dict (rather than just a dict as a
    module-level variable) so that if one test method modifies the dict the
    next test method gets a new clean copy.

    '''
    return {('other key',): 'other value'}


def _errors():
    '''Return an errors dict with some arbitrary errors in it, suitable to be
    passed to validators for testing.

    This is a function that returns a dict (rather than just a dict as a
    module-level variable) so that if one test method modifies the dict the
    next test method gets a new clean copy.

    '''
    return {('other key',): ['other error']}


class TestValidators(object):

    def test_ignore_missing_with_value_missing(self):
        '''ignore_missing() should raise StopOnError if:

        - data[key] is None, or
        - data[key] is dictization_functions.missing, or
        - key is not in data

        '''
        import ckan.lib.navl.dictization_functions as df
        import ckan.lib.navl.validators as validators

        for value in (None, df.missing, 'skip'):

            # This is the key for the value that is going to be validated.
            key = ('key to be validated',)

            # The data to pass to the validator function for validation.
            data = _data()
            if value != 'skip':
                data[key] = value

            # The errors dict to pass to the validator function.
            errors = _errors()
            errors[key] = []

            # Make copies of the data and errors dicts for asserting later.
            original_data = copy.deepcopy(data)
            original_errors = copy.deepcopy(errors)

            with nose.tools.assert_raises(df.StopOnError):
                validators.ignore_missing(key=key, data=data, errors=errors,
                                          context={})

            assert key not in data, ('When given a value of {value} '
                'ignore_missing() should remove the item from the data '
                'dict'.format(value=value))

            if key in original_data:
                del original_data[key]
            assert data == original_data, ('When given a value of {value} '
                    'ignore_missing() should not modify other items in the '
                    'data dict'.format(value=value))

            assert errors == original_errors, ('When given a value of {value} '
                'ignore_missing should not modify the errors dict'.format(
                        value=value))

    def test_ignore_missing_with_a_value(self):
        '''If data[key] is neither None or missing, ignore_missing() should do
        nothing.

        '''
        import ckan.lib.navl.validators as validators

        key = ('key to be validated',)
        data = _data()
        data[key] = 'value to be validated'
        errors = _errors()
        errors[key] = []

        # Make copies of the data and errors dicts for asserting later.
        original_data = copy.deepcopy(data)
        original_errors = copy.deepcopy(errors)

        result = validators.ignore_missing(key=key, data=data, errors=errors,
                                           context={})

        assert result is None

        assert data == original_data, ("ignore_missing() shouldn't modify the "
                                       "data dict")

        assert errors == original_errors, ("ignore_missing() shouldn't modify "
                                           "the errors dict")

    def test_name_validator_with_invalid_value(self):
        '''If given an invalid value name_validator() should do raise Invalid.

        '''
        import ckan.logic.validators as validators
        import ckan.lib.navl.dictization_functions as df
        import ckan.model as model

        invalid_values = [
            # Non-string names aren't allowed as names.
            13,
            23.7,
            100L,
            1.0j,
            None,
            True,
            False,
            ('a', 2, False),
            [13, None, True],
            {'foo': 'bar'},
            lambda x: x**2,

            # Certain reserved strings aren't allowed as names.
            'new',
            'edit',
            'search',

            # Strings < 2 characters long aren't allowed as names.
            '',
            'a',
            '2',

            # Strings > PACKAGE_NAME_MAX_LENGTH long aren't allowed as names.
            'a' * (model.PACKAGE_NAME_MAX_LENGTH + 1),

            # Strings containing non-ascii characters aren't allowed as names.
            u"fred_❤%'\"Ußabc@fred.com",

            # Strings containing upper-case characters aren't allowed as names.
            'seanH',

            # Strings containing spaces aren't allowed as names.
            'sean h',

            # Strings containing punctuation aren't allowed as names.
            'seanh!',
        ]

        for invalid_value in invalid_values:
            with nose.tools.assert_raises(df.Invalid):
                validators.name_validator(invalid_value, context={})

    def test_name_validator_with_valid_value(self):
        '''If given a valid string name_validator() should do nothing and
        return the string.

        '''
        import ckan.logic.validators as validators
        import ckan.model as model

        valid_names = [
            'fred',
            'fred-flintstone',
            'fred_flintstone',
            'fred_flintstone-9',
            'f' * model.PACKAGE_NAME_MAX_LENGTH,
            '-' * model.PACKAGE_NAME_MAX_LENGTH,
            '_' * model.PACKAGE_NAME_MAX_LENGTH,
            '9' * model.PACKAGE_NAME_MAX_LENGTH,
            '99',
            '--',
            '__',
            u'fred-flintstone_9',
        ]

        for valid_name in valid_names:
            result = validators.name_validator(valid_name, context={})
            assert result == valid_name, ('If given a valid string '
                'name_validator() should return the string unmodified.')
