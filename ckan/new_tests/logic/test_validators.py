# -*- coding: utf-8 -*-
'''Unit tests for ckan/logic/validators.py.

'''
import copy

import mock
import nose.tools

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


def returns_arg(message):
    '''A decorator that tests that the decorated function returns the argument
    that it is called with, unmodified.

    :param message: the message that will be printed if the function doesn't
        return the same argument that it was called with and the assert fails
    :type message: string

    Usage:

        @returns_arg('user_name_validator() should return the same arg that '
                     'it is called with, when called with a valid arg')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(function):
        def call_and_assert(arg, context=None):
            if context is None:
                context = {}
            result = function(arg, context=context)
            assert result == arg, message
            return result
        return call_and_assert
    return decorator


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


def raises_Invalid(function):
    '''A decorator that asserts that the decorated function raises
    dictization_functions.Invalid.

    Usage:

        @raises_Invalid
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def call_and_assert(*args, **kwargs):
        import ckan.lib.navl.dictization_functions as df
        with nose.tools.assert_raises(df.Invalid):
            return function(*args, **kwargs)
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


def does_not_modify_other_keys_in_errors_dict(message):
    '''A decorator that asserts that the decorated validator doesn't add,
    modify the value of, or remove any other keys from its `errors` dict param.

    The function *may* modify its own errors `key`.

    :param message: the message that will be printed if the function does
        modify another key in the errors dict and the assert fails
    :type message: string

    Usage:

        @does_not_modify_other_keys_in_errors_dict('user_name_validator() '
            'should not modify other keys in the errors dict')
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
            # Copy the errors dict because we don't want to modify it.
            errors = copy.deepcopy(errors)
            errors[key] = []
            assert errors == original_errors_dict, message
            return result
        return call_and_assert
    return decorator


def adds_message_to_errors_dict(error_message, message):
    '''A decorator that asserts the the decorated validator adds a given
    error message to the `errors` dict.

    :param error_message: the error message that the validator is expected to
        add to the `errors` dict
    :type error_message: string

    :param message: the message that will be printed if the function doesn't
        add the right error message to the errors dict, and the assert fails
    :type message: string

    Usage:

        @adds_message_to_errors_dict('That login name is not available.',
            'user_name_validator() should add to the errors dict when called '
            'with a user name with already exists')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(validator):
        def call_and_assert(key, data, errors, context):
            result = validator(key, data, errors, context)
            assert errors[key] == [error_message], message
            return result
        return call_and_assert
    return decorator


def returns_arg(message):
    '''A decorator that tests that the decorated function returns the argument
    that it is called with, unmodified.

    :param message: the message that will be printed if the function doesn't
        return the same argument that it was called with and the assert fails
    :type message: string

    Usage:

        @returns_arg('user_name_validator() should return the same arg that '
                     'it is called with, when called with a valid arg')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(function):
        def call_and_assert(arg, context=None):
            if context is None:
                context = {}
            result = function(arg, context=context)
            assert result == arg, message
            return result
        return call_and_assert
    return decorator


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


def raises_Invalid(function):
    '''A decorator that asserts that the decorated function raises
    dictization_functions.Invalid.

    Usage:

        @raises_Invalid
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def call_and_assert(*args, **kwargs):
        import ckan.lib.navl.dictization_functions as df
        with nose.tools.assert_raises(df.Invalid):
            return function(*args, **kwargs)
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


def does_not_modify_other_keys_in_errors_dict(message):
    '''A decorator that asserts that the decorated validator doesn't add,
    modify the value of, or remove any other keys from its `errors` dict param.

    The function *may* modify its own errors `key`.

    :param message: the message that will be printed if the function does
        modify another key in the errors dict and the assert fails
    :type message: string

    Usage:

        @does_not_modify_other_keys_in_errors_dict('user_name_validator() '
            'should not modify other keys in the errors dict')
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
            # Copy the errors dict because we don't want to modify it.
            errors = copy.deepcopy(errors)
            errors[key] = []
            assert errors == original_errors_dict, message
            return result
        return call_and_assert
    return decorator


def adds_message_to_errors_dict(error_message, message):
    '''A decorator that asserts the the decorated validator adds a given
    error message to the `errors` dict.

    :param error_message: the error message that the validator is expected to
        add to the `errors` dict
    :type error_message: string

    :param message: the message that will be printed if the function doesn't
        add the right error message to the errors dict, and the assert fails
    :type message: string

    Usage:

        @adds_message_to_errors_dict('That login name is not available.',
            'user_name_validator() should add to the errors dict when called '
            'with a user name with already exists')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(validator):
        def call_and_assert(key, data, errors, context):
            result = validator(key, data, errors, context)
            assert errors[key] == [error_message], message
            return result
        return call_and_assert
    return decorator


class TestValidators(object):

    @classmethod
    def setup_class(cls):
        # Initialize the test db (if it isn't already) and clean out any data
        # left in it.
        helpers.reset_db()

    def setup(self):
        import ckan.model as model
        # Reset the db before each test method.
        model.repo.rebuild_db()

    def test_name_validator_with_invalid_value(self):
        '''If given an invalid value name_validator() should do raise Invalid.

        '''
        import ckan.logic.validators as validators
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
            @raises_Invalid
            def call_validator(*args, **kwargs):
                return validators.name_validator(*args, **kwargs)
            call_validator(invalid_value, context={})

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
            @returns_arg('If given a valid string name_validator() should '
                         'return the string unmodified')
            def call_validator(*args, **kwargs):
                return validators.name_validator(*args, **kwargs)
            call_validator(valid_name)

    def test_user_name_validator_with_non_string_value(self):
        '''user_name_validator() should raise Invalid if given a non-string
        value.

        '''
        import ckan.logic.validators as validators

        non_string_values = [
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
        ]

        # Mock ckan.model.
        mock_model = mock.MagicMock()
        # model.User.get(some_user_id) needs to return None for this test.
        mock_model.User.get.return_value = None

        key = ('name',)
        for non_string_value in non_string_values:
            data = factories.validator_data_dict()
            data[key] = non_string_value
            errors = factories.validator_errors_dict()
            errors[key] = []

            @does_not_modify_errors_dict('user_name_validator() should not '
                                         'modify the errors dict')
            @does_not_modify_data_dict('user_name_validator() should not '
                                       'modify the data dict')
            @raises_Invalid
            def call_validator(*args, **kwargs):
                return validators.user_name_validator(*args, **kwargs)
            call_validator(key, data, errors, context={'model': mock_model})

    def test_user_name_validator_with_a_name_that_already_exists(self):
        '''user_name_validator() should add to the errors dict if given a
        user name that already exists.

        '''
        import ckan.logic.validators as validators

        # Mock ckan.model. model.User.get('user_name') will return another mock
        # object rather than None, which will simulate an existing user with
        # the same user name in the database.
        mock_model = mock.MagicMock()

        data = factories.validator_data_dict()
        key = ('name',)
        data[key] = 'user_name'
        errors = factories.validator_errors_dict()
        errors[key] = []

        @does_not_modify_other_keys_in_errors_dict('user_name_validator() '
                'should not modify other keys in the errors dict')
        @does_not_modify_data_dict('user_name_validator() should not modify '
                                   'the data dict')
        @returns_None('user_name_validator() should return None if called '
                      'with a user name that already exists')
        @adds_message_to_errors_dict('That login name is not available.',
                'user_name_validator() should add to the errors dict when '
                'called with the name of a user that already exists')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors, context={'model': mock_model})

    def test_user_name_validator_successful(self):
        '''user_name_validator() should do nothing if given a valid name.'''

        import ckan.logic.validators as validators

        data = factories.validator_data_dict()
        key = ('name',)
        data[key] = 'new_user_name'
        errors = factories.validator_errors_dict()
        errors[key] = []

        # Mock ckan.model.
        mock_model = mock.MagicMock()
        # model.User.get(user_name) should return None, to simulate that no
        # user with that name exists in the database.
        mock_model.User.get.return_value = None

        @does_not_modify_errors_dict('user_name_validator() should not '
                                     'modify the errors dict when given '
                                     'valid input')
        @does_not_modify_data_dict('user_name_validator() should not modify '
                                   'the data dict when given valid input')
        @returns_None('user_name_validator() should return None when given '
                      'valid input')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors, context={'model': mock_model})

    # TODO: Test user_name_validator()'s behavior when there's a 'user_obj' in
    # the context dict.
