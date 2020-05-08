# encoding: utf-8

"""Unit tests for ckan/lib/navl/validators.py.

"""
import copy

import pytest
import ckan.tests.factories as factories
import ckan.lib.navl.validators as validators


def returns_None(function):
    """A decorator that asserts that the decorated function returns None.

    :param function: the function to decorate
    :type function: function

    Usage:

        @returns_None
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def call_and_assert(*args, **kwargs):
        original_args = copy.deepcopy(args)
        original_kwargs = copy.deepcopy(kwargs)

        result = function(*args, **kwargs)

        assert result is None, (
            "Should return None when called with args: {args} and "
            "kwargs: {kwargs}".format(
                args=original_args, kwargs=original_kwargs
            )
        )
        return result

    return call_and_assert


def raises_StopOnError(function):
    """A decorator that asserts that the decorated function raises
    dictization_functions.StopOnError.

    :param function: the function to decorate
    :type function: function

    Usage:

        @raises_StopOnError
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def call_and_assert(*args, **kwargs):
        import ckan.lib.navl.dictization_functions as df

        with pytest.raises(df.StopOnError):
            function(*args, **kwargs)

    return call_and_assert


def does_not_modify_data_dict(validator):
    """A decorator  that asserts that the decorated validator doesn't modify
    its `data` dict param.

    :param validator: the validator function to decorate
    :type validator: function

    Usage:

        @does_not_modify_data_dict
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def call_and_assert(key, data, errors, context=None):
        if context is None:
            context = {}
        original_data = copy.deepcopy(data)
        original_errors = copy.deepcopy(errors)
        original_context = copy.deepcopy(context)

        result = validator(key, data, errors, context=context)

        assert data == original_data, (
            "Should not modify data dict when called with "
            "key: {key}, data: {data}, errors: {errors}, "
            "context: {context}".format(
                key=key,
                data=original_data,
                errors=original_errors,
                context=original_context,
            )
        )
        return result

    return call_and_assert


def removes_key_from_data_dict(validator):
    """A decorator  that asserts that the decorated validator removes its key
    from the data dict.

    :param validator: the validator function to decorate
    :type validator: function

    Usage:

        @removes_key_from_data_dict
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def call_and_assert(key, data, errors, context=None):
        if context is None:
            context = {}
        original_data = copy.deepcopy(data)
        original_errors = copy.deepcopy(errors)
        original_context = copy.deepcopy(context)

        result = validator(key, data, errors, context=context)

        assert key not in data, (
            "Should remove key from data dict when called with: "
            "key: {key}, data: {data}, errors: {errors}, "
            "context: {context} ".format(
                key=key,
                data=original_data,
                errors=original_errors,
                context=original_context,
            )
        )
        return result

    return call_and_assert


def does_not_modify_other_keys_in_data_dict(validator):
    """A decorator that asserts that the decorated validator doesn't add,
    modify the value of, or remove any other keys from its ``data`` dict param.

    The function *may* modify its own data dict key.

    :param validator: the validator function to decorate
    :type validator: function

    Usage:

        @does_not_modify_other_keys_in_data_dict
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def call_and_assert(key, data, errors, context=None):
        if context is None:
            context = {}
        original_data = copy.deepcopy(data)
        original_errors = copy.deepcopy(errors)
        original_context = copy.deepcopy(context)

        result = validator(key, data, errors, context=context)

        # The validator function is allowed to modify its own key, so remove
        # that key from both dicts for the purposes of the assertions below.
        if key in data:
            del data[key]
        if key in original_data:
            del original_data[key]

        assert data.keys() == original_data.keys(), (
            "Should not add or remove keys from data dict when called with "
            "key: {key}, data: {data}, errors: {errors}, "
            "context: {context}".format(
                key=key,
                data=original_data,
                errors=original_errors,
                context=original_context,
            )
        )
        for key_ in data:
            assert data[key_] == original_data[key_], (
                "Should not modify other keys in data dict when called with "
                "key: {key}, data: {data}, errors: {errors}, "
                "context: {context}".format(
                    key=key,
                    data=original_data,
                    errors=original_errors,
                    context=original_context,
                )
            )
        return result

    return call_and_assert


def does_not_modify_errors_dict(validator):
    """A decorator that asserts that the decorated validator doesn't modify its
    `errors` dict param.

    :param validator: the validator function to decorate
    :type validator: function

    Usage:

        @does_not_modify_errors_dict
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def call_and_assert(key, data, errors, context=None):
        if context is None:
            context = {}
        original_data = copy.deepcopy(data)
        original_errors = copy.deepcopy(errors)
        original_context = copy.deepcopy(context)

        result = validator(key, data, errors, context=context)

        assert errors == original_errors, (
            "Should not modify errors dict when called with key: {key}, "
            "data: {data}, errors: {errors}, "
            "context: {context}".format(
                key=key,
                data=original_data,
                errors=original_errors,
                context=original_context,
            )
        )
        return result

    return call_and_assert


class TestValidators(object):
    def test_ignore_missing_with_value_missing(self):
        """ignore_missing() should raise StopOnError if:

        - data[key] is None, or
        - data[key] is dictization_functions.missing, or
        - key is not in data

        """
        import ckan.lib.navl.dictization_functions as df

        for value in (None, df.missing, "skip"):

            # This is the key for the value that is going to be validated.
            key = ("key to be validated",)

            # The data to pass to the validator function for validation.
            data = factories.validator_data_dict()
            if value != "skip":
                data[key] = value

            # The errors dict to pass to the validator function.
            errors = factories.validator_errors_dict()
            errors[key] = []

            @does_not_modify_other_keys_in_data_dict
            @does_not_modify_errors_dict
            @removes_key_from_data_dict
            @raises_StopOnError
            def call_validator(*args, **kwargs):
                return validators.ignore_missing(*args, **kwargs)

            call_validator(key=key, data=data, errors=errors, context={})

    def test_ignore_missing_with_a_value(self):
        """If data[key] is neither None or missing, ignore_missing() should do
        nothing.

        """
        key = ("key to be validated",)
        data = factories.validator_data_dict()
        data[key] = "value to be validated"
        errors = factories.validator_errors_dict()
        errors[key] = []

        @returns_None
        @does_not_modify_data_dict
        @does_not_modify_errors_dict
        def call_validator(*args, **kwargs):
            return validators.ignore_missing(*args, **kwargs)

        call_validator(key=key, data=data, errors=errors, context={})


class TestDefault(object):
    def test_key_doesnt_exist(self):
        dict_ = {}
        validators.default("default_value")("key", dict_, {}, {})
        assert dict_ == {"key": "default_value"}

    def test_value_is_none(self):
        dict_ = {"key": None}
        validators.default("default_value")("key", dict_, {}, {})
        assert dict_ == {"key": "default_value"}

    def test_value_is_empty_string(self):
        dict_ = {"key": ""}
        validators.default("default_value")("key", dict_, {}, {})
        assert dict_ == {"key": "default_value"}

    def test_value_is_false(self):
        # False is a consciously set value, so should not be changed to the
        # default
        dict_ = {"key": False}
        validators.default("default_value")("key", dict_, {}, {})
        assert dict_ == {"key": False}

    def test_already_has_a_value(self):
        dict_ = {"key": "original"}
        validators.default("default_value")("key", dict_, {}, {})
        assert dict_ == {"key": "original"}
