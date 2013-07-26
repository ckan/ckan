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

        key = ('foo',)
        data = {key: 'bar'}
        errors = {key: []}

        result = validators.ignore_missing(key=key, data=data, errors=errors,
                                           context={})

        assert result is None

        # ignore_missing shouldn't remove or modify the value.
        assert data.get(key) == 'bar'

        # ignore_missing shouldn't add any errors.
        assert errors[key] == []
