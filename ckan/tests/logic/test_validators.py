# encoding: utf-8

'''Unit tests for ckan/logic/validators.py.

'''
import copy
import decimal
import fractions
import warnings

import ckan.lib.navl.dictization_functions as df
import ckan.logic.validators as validators
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.tests.lib.navl.test_validators as t
import mock
import nose.tools

assert_equals = nose.tools.assert_equals


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

    # START-AFTER

    def test_user_name_validator_with_non_string_value(self):
        '''user_name_validator() should raise Invalid if given a non-string
        value.

        '''
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

    # END-BEFORE

    def test_user_name_validator_with_a_name_that_already_exists(self):
        '''user_name_validator() should add to the errors dict if given a
        user name that already exists.

        '''
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

    def test_if_empty_guess_format(self):
        data = {'name': 'package_name', 'resources': [
            {'url': 'http://fakedomain/my.csv', 'format': ''},
            {'url': 'http://fakedomain/my.pdf',
             'format': df.Missing},
            {'url': 'http://fakedomain/my.pdf', 'format': 'pdf'},
            {'url': 'http://fakedomain/my.pdf',
             'id': 'fake_resource_id', 'format': ''}
        ]}
        data = df.flatten_dict(data)

        @t.does_not_modify_errors_dict
        def call_validator(*args, **kwargs):
            return validators.if_empty_guess_format(*args, **kwargs)

        new_data = copy.deepcopy(data)
        call_validator(key=('resources', 0, 'format'), data=new_data,
                       errors={}, context={})
        assert new_data[('resources', 0, 'format')] == 'text/csv'

        new_data = copy.deepcopy(data)
        call_validator(key=('resources', 1, 'format'), data=new_data,
                       errors={}, context={})
        assert new_data[('resources', 1, 'format')] == 'application/pdf'

        new_data = copy.deepcopy(data)
        call_validator(key=('resources', 2, 'format'), data=new_data,
                       errors={}, context={})
        assert new_data[('resources', 2, 'format')] == 'pdf'

        new_data = copy.deepcopy(data)
        call_validator(key=('resources', 3, 'format'), data=new_data,
                       errors={}, context={})
        assert new_data[('resources', 3, 'format')] == ''

    def test_clean_format(self):
        format = validators.clean_format('csv')
        assert format == 'CSV'

        format = validators.clean_format('text/csv')
        assert format == 'CSV'

        format = validators.clean_format('not a format')
        assert format == 'not a format'

        format = validators.clean_format('')
        assert format == ''

    def test_datasets_with_org_can_be_private_when_creating(self):
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


class TestIntValidator(object):

    def test_int_unchanged(self):
        returns_arg(validators.int_validator)(42)

    def test_zero_unchanged(self):
        returns_arg(validators.int_validator)(0)

    def test_long_unchanged(self):
        returns_arg(validators.int_validator)(3948756923874659827346598)

    def test_None_unchanged(self):
        returns_arg(validators.int_validator)(None)

    def test_float_converted(self):
        assert_equals(validators.int_validator(42.0, None), 42)

    def test_fraction_converted(self):
        assert_equals(validators.int_validator(
            fractions.Fraction(2, 1), {}), 2)

    def test_decimal_converted(self):
        assert_equals(validators.int_validator(
            decimal.Decimal('19.00'), {}), 19)

    def test_long_int_string_converted(self):
        assert_equals(validators.int_validator(
            '528735648764587235684376', {}), 528735648764587235684376)

    def test_negative_int_string_converted(self):
        assert_equals(validators.int_validator('-2', {}), -2)

    def test_positive_int_string_converted(self):
        assert_equals(validators.int_validator('+3', {}), 3)

    def test_zero_prefixed_int_string_converted_as_decimal(self):
        assert_equals(validators.int_validator('0123', {}), 123)

    def test_string_with_whitespace_converted(self):
        assert_equals(validators.int_validator('\t  98\n', {}), 98)

    def test_empty_string_becomes_None(self):
        assert_equals(validators.int_validator('', {}), None)

    def test_whitespace_string_becomes_None(self):
        assert_equals(validators.int_validator('\n\n  \t', {}), None)

    def test_float_with_decimal_raises_Invalid(self):
        raises_Invalid(validators.int_validator)(42.5, {})

    def test_float_string_raises_Invalid(self):
        raises_Invalid(validators.int_validator)('42.0', {})

    def test_exponent_string_raises_Invalid(self):
        raises_Invalid(validators.int_validator)('1e6', {})

    def test_non_numeric_string_raises_Invalid(self):
        raises_Invalid(validators.int_validator)('text', {})

    def test_non_whole_fraction_raises_Invalid(self):
        raises_Invalid(validators.int_validator)(fractions.Fraction(3, 2), {})

    def test_non_whole_decimal_raises_Invalid(self):
        raises_Invalid(validators.int_validator)(decimal.Decimal('19.99'), {})

    def test_complex_with_imaginary_component_raises_Invalid(self):
        with warnings.catch_warnings():  # divmod() issues warning for complex
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            raises_Invalid(validators.int_validator)(1 + 1j, {})

    def test_complex_without_imaginary_component_raises_Invalid(self):
        with warnings.catch_warnings():  # divmod() issues warning for complex
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            raises_Invalid(validators.int_validator)(1 + 0j, {})


class TestBoolValidator(object):

    def test_bool_true(self):
        assert_equals(validators.boolean_validator(True, None), True)

    def test_bool_false(self):
        assert_equals(validators.boolean_validator(False, None), False)

    def test_missing(self):
        assert_equals(validators.boolean_validator('', None), False)

    def test_none(self):
        assert_equals(validators.boolean_validator(None, None), False)

    def test_string_true(self):
        assert_equals(validators.boolean_validator('true', None), True)
        assert_equals(validators.boolean_validator('yes', None), True)
        assert_equals(validators.boolean_validator('t', None), True)
        assert_equals(validators.boolean_validator('y', None), True)
        assert_equals(validators.boolean_validator('1', None), True)

    def test_string_false(self):
        assert_equals(validators.boolean_validator('f', None), False)


class TestExistsValidator(helpers.FunctionalTestBase):

    def _make_context(self):
        return {
            'model': model,
            'session': model.Session
        }

    @nose.tools.raises(df.Invalid)
    def test_package_name_exists_empty(self):
        ctx = self._make_context()
        v = validators.package_name_exists('', ctx)

    def test_package_name_exists(self):
        name = 'pne_validation_test'
        dataset = factories.Dataset(name=name)
        ctx = self._make_context()
        v = validators.package_name_exists(name, ctx)
        assert v == name

    @nose.tools.raises(df.Invalid)
    def test_resource_id_exists_empty(self):
        ctx = self._make_context()
        v = validators.resource_id_exists('', ctx)

    def test_resource_id_exists(self):
        resource = factories.Resource()
        ctx = self._make_context()
        v = validators.resource_id_exists(resource['id'], ctx)
        assert v == resource['id']

    @nose.tools.raises(df.Invalid)
    def test_user_id_or_name_exists_empty(self):
        ctx = self._make_context()
        v = validators.user_id_or_name_exists('', ctx)

    def test_user_id_or_name_exists(self):
        user = factories.User(name='username')
        ctx = self._make_context()
        v = validators.user_id_or_name_exists(user['id'], ctx)
        assert v == user['id']
        v = validators.user_id_or_name_exists(user['name'], ctx)
        assert v == user['name']

    @nose.tools.raises(df.Invalid)
    def test_group_id_or_name_exists_empty(self):
        ctx = self._make_context()
        v = validators.user_id_or_name_exists('', ctx)

    def test_group_id_or_name_exists(self):
        group = factories.Group()
        ctx = self._make_context()
        v = validators.group_id_or_name_exists(group['id'], ctx)
        assert v == group['id']

        v = validators.group_id_or_name_exists(group['name'], ctx)
        assert v == group['name']

    @nose.tools.raises(df.Invalid)
    def test_role_exists_empty(self):
        ctx = self._make_context()
        v = validators.role_exists('', ctx)

# TODO: Need to test when you are not providing owner_org and the validator queries for the dataset with package_show
