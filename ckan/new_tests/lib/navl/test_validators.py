# -*- coding: utf-8 -*-
'''Unit tests for ckan/lib/navl/validators.py.

'''
import copy

import nose.tools

import ckan.new_tests.factories as factories


def returns_None(message):
    '''A decorator that asserts that the decorated function returns None.

    :param message: the message that will be printed if the function doesn't
        return None and the assert fails
    :type message: string

    Usage:

        @returns_None('user_name_validator() should return None when given '
                       'valid input')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(function):
        def call_and_assert(*args, **kwargs):
            result = function(*args, **kwargs)
            assert result is None, message
            return result
        return call_and_assert
    return decorator


def raises_StopOnError(function):
    '''A decorator that asserts that the decorated function raises
    dictization_functions.StopOnError.

    Usage:

        @raises_StopOnError
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def call_and_assert(*args, **kwargs):
        import ckan.lib.navl.dictization_functions as df
        nose.tools.assert_raises(df.StopOnError, function, *args, **kwargs)
    return call_and_assert


def does_not_modify_data_dict(message):
    '''A decorator  that asserts that the decorated validator doesn't modify
    its `data` dict param.

    :param message: the message that will be printed if the function does
        modify the data dict and the assert fails
    :type message: string

    Usage:

        @does_not_modify_data_dict('user_name_validator() should not modify '
                                   'the data dict')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(validator):
        def call_and_assert(key, data, errors, context=None):
            if context is None:
                context = {}
            # Make a copy of the data dict so we can assert against it later.
            original_data_dict = copy.deepcopy(data)
            result = validator(key, data, errors, context=context)
            assert data == original_data_dict, message
            return result
        return call_and_assert
    return decorator


def removes_key_from_data_dict(message):
    '''A decorator  that asserts that the decorated validator removes its key
    from the data dict.

    :param message: the message that will be printed if the function does not
        remove its key and the assert fails
    :type message: string

    Usage:

        @removes_key_from_data_dict('user_name_validator() should remove its '
                                    'key from the data dict')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(validator):
        def call_and_assert(key, data, errors, context=None):
            if context is None:
                context = {}
            result = validator(key, data, errors, context=context)
            assert key not in data, message
            return result
        return call_and_assert
    return decorator


def does_not_modify_other_keys_in_data_dict(message):
    '''A decorator that asserts that the decorated validator doesn't add,
    modify the value of, or remove any other keys from its ``data`` dict param.

    The function *may* modify its own data dict key.

    :param message: the message that will be printed if the function does
        modify another key in the data dict and the assert fails
    :type message: string

    Usage:

        @does_not_modify_other_keys_in_data_dict('user_name_validator() '
            'should not modify other keys in the data dict')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(validator):
        def call_and_assert(key, data, errors, context=None):
            if context is None:
                context = {}
            # Make a copy of the data dict so we can assert against it later.
            original_data_dict = copy.deepcopy(data)
            if key in original_data_dict:
                del original_data_dict[key]
            result = validator(key, data, errors, context=context)
            assert data == original_data_dict, message
            return result
        return call_and_assert
    return decorator


def does_not_modify_errors_dict(message):
    '''A decorator that asserts that the decorated validator doesn't modify its
    `errors` dict param.

    :param message: the message that will be printed if the function does
        modify the errors dict and the assert fails
    :type message: string

    Usage:

        @does_not_modify_errors_dict('user_name_validator() should not modify '
                                     'the errors dict')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(validator):
        def call_and_assert(key, data, errors, context=None):
            if context is None:
                context = {}
            # Make a copy of the errors dict so we can assert against it later.
            original_errors_dict = copy.deepcopy(errors)
            result = validator(key, data, errors, context=context)
            assert errors == original_errors_dict, message
            return result
        return call_and_assert
    return decorator


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

            @does_not_modify_other_keys_in_data_dict(
                'When given a value of {value} ignore_missing() should '
                'not modify other items in the data dict'.format(
                    value=repr(value)))
            @does_not_modify_errors_dict(
                'When given a value of {value} ignore_missing() should not '
                'modify the errors dict'.format(value=repr(value)))
            @removes_key_from_data_dict(
                'When given a value of {value} ignore_missing() should remove '
                'the item from the data dict'.format(value=repr(value)))
            @raises_StopOnError
            def call_validator(*args, **kwargs):
                return validators.ignore_missing(*args, **kwargs)
            call_validator(key=key, data=data, errors=errors, context={})

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

        @returns_None('When called with (non-missing) value, ignore_missing() '
                      'should return None')
        @does_not_modify_data_dict("ignore_missing() shouldn't modify the "
                                   'data dict')
        @does_not_modify_errors_dict("ignore_missing() shouldn't modify the "
                                     'errors dict')
        def call_validator(*args, **kwargs):
            return validators.ignore_missing(*args, **kwargs)
        call_validator(key=key, data=data, errors=errors, context={})
