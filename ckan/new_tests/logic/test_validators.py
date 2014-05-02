# -*- coding: utf-8 -*-
'''Unit tests for ckan/logic/validators.py.

'''
import copy

import mock
import nose.tools

import ckan.new_tests.factories as factories
# Import some test helper functions from another module.
# This is bad (test modules shouldn't share code with eachother) but because of
# the way validator functions are organised in CKAN (in different modules in
# different places in the code) we have to either do this or introduce a shared
# test helper functions module (which we also don't want to do).
import ckan.new_tests.lib.navl.test_validators as t


def returns_arg(function):
    '''A decorator that tests that the decorated function returns the argument
    that it is called with, unmodified.

    :param function: the function to decorate
    :type function: function

    Usage:

        @returns_arg
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def call_and_assert(arg, context=None):
        if context is None:
            context = {}
        result = function(arg, context=context)
        assert result == arg, (
            'Should return the argument that was passed to it, unchanged '
            '({arg})'.format(arg=repr(arg)))
        return result
    return call_and_assert


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
        nose.tools.assert_raises(df.Invalid, function, *args, **kwargs)
    return call_and_assert


def does_not_modify_other_keys_in_errors_dict(validator):
    '''A decorator that asserts that the decorated validator doesn't add,
    modify the value of, or remove any other keys from its ``errors`` dict
    param.

    The function *may* modify its own errors dict key.

    :param validator: the validator function to decorate
    :type validator: function

    Usage:

        @does_not_modify_other_keys_in_errors_dict
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def call_and_assert(key, data, errors, context=None):
        if context is None:
            context = {}
        original_data = copy.deepcopy(data)
        original_errors = copy.deepcopy(errors)
        original_context = copy.deepcopy(context)

        result = validator(key, data, errors, context=context)

        # The validator function is allowed to modify its own key, so remove
        # that key from both dicts for the purposes of the assertions below.
        if key in errors:
            del errors[key]
        if key in original_errors:
            del original_errors[key]

        assert errors.keys() == original_errors.keys(), (
            'Should not add or remove keys from errors dict when called with '
            'key: {key}, data: {data}, errors: {errors}, '
            'context: {context}'.format(key=key, data=original_data,
                                        errors=original_errors,
                                        context=original_context))
        for key_ in errors:
            assert errors[key_] == original_errors[key_], (
                'Should not modify other keys in errors dict when called with '
                'key: {key}, data: {data}, errors: {errors}, '
                'context: {context}'.format(key=key, data=original_data,
                                            errors=original_errors,
                                            context=original_context))
        return result
    return call_and_assert


def adds_message_to_errors_dict(error_message):
    '''A decorator that asserts the the decorated validator adds a given
    error message to the `errors` dict.

    :param error_message: the error message that the validator is expected to
        add to the `errors` dict
    :type error_message: string

    Usage:

        @adds_message_to_errors_dict('That login name is not available.')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    '''
    def decorator(validator):
        def call_and_assert(key, data, errors, context):
            result = validator(key, data, errors, context)
            assert errors[key] == [error_message], (
                'Should add message to errors dict: {msg}'.format(
                    msg=error_message))
            return result
        return call_and_assert
    return decorator


class TestValidators(object):

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
            lambda x: x ** 2,

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
            @returns_arg
            def call_validator(*args, **kwargs):
                return validators.name_validator(*args, **kwargs)
            call_validator(valid_name)

    ## START-AFTER

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
            lambda x: x ** 2,
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

            @t.does_not_modify_data_dict
            @raises_Invalid
            def call_validator(*args, **kwargs):
                return validators.user_name_validator(*args, **kwargs)
            call_validator(key, data, errors, context={'model': mock_model})

    ## END-BEFORE

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

        @does_not_modify_other_keys_in_errors_dict
        @t.does_not_modify_data_dict
        @t.returns_None
        @adds_message_to_errors_dict('That login name is not available.')
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

        @t.does_not_modify_errors_dict
        @t.does_not_modify_data_dict
        @t.returns_None
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors, context={'model': mock_model})

    # TODO: Test user_name_validator()'s behavior when there's a 'user_obj' in
    # the context dict.

    def test_datasets_with_org_can_be_private_when_creating(self):

        import ckan.logic.validators as validators

        data = factories.validator_data_dict()
        errors = factories.validator_errors_dict()

        key = ('private',)
        data[key] = True
        errors[key] = []

        data[('owner_org',)] = 'some_org_id'

        # Mock ckan.model.
        mock_model = mock.MagicMock()

        @t.does_not_modify_errors_dict
        @t.does_not_modify_data_dict
        @t.returns_None
        def call_validator(*args, **kwargs):
            return validators.datasets_with_no_organization_cannot_be_private(
                *args, **kwargs)
        call_validator(key, data, errors, context={'model': mock_model})

    def test_datasets_with_no_org_cannot_be_private_when_creating(self):

        import ckan.logic.validators as validators

        data = factories.validator_data_dict()
        errors = factories.validator_errors_dict()

        key = ('private',)
        data[key] = True
        errors[key] = []

        # Mock ckan.model.
        mock_model = mock.MagicMock()

        @t.does_not_modify_data_dict
        @adds_message_to_errors_dict(
            "Datasets with no organization can't be private.")
        def call_validator(*args, **kwargs):
            return validators.datasets_with_no_organization_cannot_be_private(
                *args, **kwargs)

        call_validator(key, data, errors, context={'model': mock_model})

    def test_datasets_with_org_can_be_private_when_updating(self):

        import ckan.logic.validators as validators

        data = factories.validator_data_dict()
        errors = factories.validator_errors_dict()

        key = ('private',)
        data[key] = True
        errors[key] = []

        data[('id',)] = 'some_dataset_id'
        data[('owner_org',)] = 'some_org_id'

        # Mock ckan.model.
        mock_model = mock.MagicMock()

        @t.does_not_modify_errors_dict
        @t.does_not_modify_data_dict
        @t.returns_None
        def call_validator(*args, **kwargs):
            return validators.datasets_with_no_organization_cannot_be_private(
                *args, **kwargs)
        call_validator(key, data, errors, context={'model': mock_model})

    #TODO: Need to test when you are not providing owner_org and the validator
    #      queries for the dataset with package_show
