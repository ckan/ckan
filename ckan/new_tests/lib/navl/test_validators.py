# -*- coding: utf-8 -*-
'''Unit tests for ckan/lib/navl/validators.py.

'''
import copy

import nose.tools

import ckan.new_tests.factories as factories


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
            data = factories.validator_data_dict()
            if value != 'skip':
                data[key] = value

            # The errors dict to pass to the validator function.
            errors = factories.validator_errors_dict()
            errors[key] = []

            # Make copies of the data and errors dicts for asserting later.
            original_data = copy.deepcopy(data)
            original_errors = copy.deepcopy(errors)

            with nose.tools.assert_raises(df.StopOnError) as context:
                validators.ignore_missing(key=key, data=data, errors=errors,
                                          context={})

            assert key not in data, ('When given a value of {value} '
                                     'ignore_missing() should remove the item '
                                     'from the data dict'.format(value=value))

            if key in original_data:
                del original_data[key]
            assert data == original_data, ('When given a value of {value} '
                                           'ignore_missing() should not '
                                           'modify other items in the '
                                           'data dict'.format(value=value))

            assert errors == original_errors, ('When given a value of {value} '
                                               'ignore_missing should not '
                                               'modify the errors '
                                               'dict'.format(value=value))

    def test_ignore_missing_with_a_value(self):
        '''If data[key] is neither None or missing, ignore_missing() should do
        nothing.

        '''
        import ckan.lib.navl.validators as validators

        key = ('key to be validated',)
        data = factories.validator_data_dict()
        data[key] = 'value to be validated'
        errors = factories.validator_errors_dict()
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
