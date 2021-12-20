# encoding: utf-8
"""Unit tests for ckan/logic/validators.py.

"""
import warnings

import copy
import decimal
import fractions
import mock
import pytest

import ckan.lib.navl.dictization_functions as df
import ckan.logic.validators as validators
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.tests.lib.navl.test_validators as t
import ckan.logic as logic


def returns_arg(function):
    """A decorator that tests that the decorated function returns the argument
    that it is called with, unmodified.

    :param function: the function to decorate
    :type function: function

    Usage:

        @returns_arg
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def call_and_assert(arg, context=None):
        if context is None:
            context = {}
        result = function(arg, context=context)
        assert result == arg, (
            "Should return the argument that was passed to it, unchanged "
            "({arg})".format(arg=repr(arg))
        )
        return result

    return call_and_assert


def raises_Invalid(function):
    """A decorator that asserts that the decorated function raises
    dictization_functions.Invalid.

    Usage:

        @raises_Invalid
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def call_and_assert(*args, **kwargs):
        with pytest.raises(df.Invalid):
            function(*args, **kwargs)

    return call_and_assert


def does_not_modify_other_keys_in_errors_dict(validator):
    """A decorator that asserts that the decorated validator doesn't add,
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
        if key in errors:
            del errors[key]
        if key in original_errors:
            del original_errors[key]

        assert errors.keys() == original_errors.keys(), (
            "Should not add or remove keys from errors dict when called with "
            "key: {key}, data: {data}, errors: {errors}, "
            "context: {context}".format(
                key=key,
                data=original_data,
                errors=original_errors,
                context=original_context,
            )
        )
        for key_ in errors:
            assert errors[key_] == original_errors[key_], (
                "Should not modify other keys in errors dict when called with "
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


def adds_message_to_errors_dict(error_message):
    """A decorator that asserts the the decorated validator adds a given
    error message to the `errors` dict.

    :param error_message: the error message that the validator is expected to
        add to the `errors` dict
    :type error_message: string

    Usage:

        @adds_message_to_errors_dict('That login name is not available.')
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)
        call_validator(key, data, errors)

    """

    def decorator(validator):
        def call_and_assert(key, data, errors, context):
            result = validator(key, data, errors, context)
            assert errors[key] == [
                error_message
            ], "Should add message to errors dict: {msg}".format(
                msg=error_message
            )
            return result

        return call_and_assert

    return decorator


@pytest.mark.usefixtures("clean_db")
def test_email_is_unique_validator_with_existed_value(app):
    with app.flask_app.test_request_context():
        user1 = factories.User(username="user01", email="user01@email.com")

        # try to create new user with occupied email
        with pytest.raises(logic.ValidationError):
            factories.User(username="new_user", email="user01@email.com")


@pytest.mark.usefixtures("clean_db")
def test_email_is_unique_validator_user_update_email_unchanged(app):
    with app.flask_app.test_request_context():
        user = factories.User(username="user01", email="user01@email.com")

        # try to update user1 and leave email unchanged
        old_email = "user01@email.com"

        helpers.call_action("user_update", **user)
        updated_user = model.User.get(user["id"])

        assert updated_user.email == old_email


@pytest.mark.usefixtures("clean_db")
def test_email_is_unique_validator_user_update_using_name_as_id(app):
    with app.flask_app.test_request_context():
        user = factories.User(username="user01", email="user01@email.com")

        # try to update user1 and leave email unchanged
        old_email = "user01@email.com"

        helpers.call_action(
            "user_update", id=user['name'], email=user['email'], about='test')
        updated_user = model.User.get(user["id"])

        assert updated_user.email == old_email
        assert updated_user.about == 'test'


@pytest.mark.usefixtures("clean_db")
def test_email_is_unique_validator_user_update_email_new(app):
    with app.flask_app.test_request_context():
        user = factories.User(username="user01", email="user01@email.com")

        # try to update user1 email to unoccupied one
        new_email = "user_new@email.com"
        user["email"] = new_email

        helpers.call_action("user_update", **user)
        updated_user = model.User.get(user["id"])

        assert updated_user.email == new_email


@pytest.mark.usefixtures("clean_db")
def test_email_is_unique_validator_user_update_to_existed_email(app):
    with app.flask_app.test_request_context():
        user1 = factories.User(username="user01", email="user01@email.com")
        user2 = factories.User(username="user02", email="user02@email.com")

        # try to update user1 email to existed one
        user1["email"] = user2["email"]

        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user1)


def test_name_validator_with_invalid_value():
    """If given an invalid value name_validator() should do raise Invalid.

    """
    invalid_values = [
        # Non-string names aren't allowed as names.
        13,
        23.7,
        100,
        1.0j,
        None,
        True,
        False,
        ("a", 2, False),
        [13, None, True],
        {"foo": "bar"},
        lambda x: x ** 2,
        # Certain reserved strings aren't allowed as names.
        "new",
        "edit",
        "search",
        # Strings < 2 characters long aren't allowed as names.
        "",
        "a",
        "2",
        # Strings > PACKAGE_NAME_MAX_LENGTH long aren't allowed as names.
        "a" * (model.PACKAGE_NAME_MAX_LENGTH + 1),
        # Strings containing non-ascii characters aren't allowed as names.
        u"fred_❤%'\"Ußabc@fred.com",
        # Strings containing upper-case characters aren't allowed as names.
        "seanH",
        # Strings containing spaces aren't allowed as names.
        "sean h",
        # Strings containing punctuation aren't allowed as names.
        "seanh!",
    ]

    for invalid_value in invalid_values:

        @raises_Invalid
        def call_validator(*args, **kwargs):
            return validators.name_validator(*args, **kwargs)

        call_validator(invalid_value, context={})


def test_email_validator_with_invalid_value():
    invalid_values = [
        "..test...test..@example.com",
        "test @example.com",
        "test@ example.com",
        "test..test@example.com",
        "test.test...@example.com",
        "...test@example.com",
    ]

    for invalid_value in invalid_values:

        @raises_Invalid
        def call_validator(*args, **kwargs):
            return validators.email_validator(*args, **kwargs)

        call_validator(invalid_value, context={})


def test_email_validator_with_valid_value():
    valid_values = [
        "text@example.com",
        "test.this@example.com",
        "test.this@server.example.com",
    ]

    for valid_value in valid_values:

        @returns_arg
        def call_validator(*args, **kwargs):
            return validators.email_validator(*args, **kwargs)

        call_validator(valid_value)


def test_name_validator_with_valid_value():
    """If given a valid string name_validator() should do nothing and
    return the string.

    """
    valid_names = [
        "fred",
        "fred-flintstone",
        "fred_flintstone",
        "fred_flintstone-9",
        "f" * model.PACKAGE_NAME_MAX_LENGTH,
        "-" * model.PACKAGE_NAME_MAX_LENGTH,
        "_" * model.PACKAGE_NAME_MAX_LENGTH,
        "9" * model.PACKAGE_NAME_MAX_LENGTH,
        "99",
        "--",
        "__",
        u"fred-flintstone_9",
    ]

    for valid_name in valid_names:

        @returns_arg
        def call_validator(*args, **kwargs):
            return validators.name_validator(*args, **kwargs)

        call_validator(valid_name)


# START-AFTER


def test_user_name_validator_with_non_string_value():
    """user_name_validator() should raise Invalid if given a non-string
    value.

    """
    non_string_values = [
        13,
        23.7,
        100,
        1.0j,
        None,
        True,
        False,
        ("a", 2, False),
        [13, None, True],
        {"foo": "bar"},
        lambda x: x ** 2,
    ]

    # Mock ckan.model.
    mock_model = mock.MagicMock()
    # model.User.get(some_user_id) needs to return None for this test.
    mock_model.User.get.return_value = None

    key = ("name",)
    for non_string_value in non_string_values:
        data = factories.validator_data_dict()
        data[key] = non_string_value
        errors = factories.validator_errors_dict()
        errors[key] = []

        @t.does_not_modify_data_dict
        @raises_Invalid
        def call_validator(*args, **kwargs):
            return validators.user_name_validator(*args, **kwargs)

        call_validator(key, data, errors, context={"model": mock_model})


# END-BEFORE


def test_user_name_validator_with_a_name_that_already_exists():
    """user_name_validator() should add to the errors dict if given a
    user name that already exists.

    """
    # Mock ckan.model. model.User.get('user_name') will return another mock
    # object rather than None, which will simulate an existing user with
    # the same user name in the database.
    mock_model = mock.MagicMock()

    data = factories.validator_data_dict()
    key = ("name",)
    data[key] = "user_name"
    errors = factories.validator_errors_dict()
    errors[key] = []

    @does_not_modify_other_keys_in_errors_dict
    @t.does_not_modify_data_dict
    @t.returns_None
    @adds_message_to_errors_dict("That login name is not available.")
    def call_validator(*args, **kwargs):
        return validators.user_name_validator(*args, **kwargs)

    call_validator(key, data, errors, context={"model": mock_model})


def test_user_name_validator_successful():
    """user_name_validator() should do nothing if given a valid name."""
    data = factories.validator_data_dict()
    key = ("name",)
    data[key] = "new_user_name"
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

    call_validator(key, data, errors, context={"model": mock_model})


# TODO: Test user_name_validator()'s behavior when there's a 'user_obj' in
# the context dict.


def test_if_empty_guess_format():
    data = {
        "name": "package_name",
        "resources": [
            {"url": "http://fakedomain/my.csv", "format": ""},
            {"url": "http://fakedomain/my.pdf", "format": df.Missing},
            {"url": "http://fakedomain/my.pdf", "format": "pdf"},
            {
                "url": "http://fakedomain/my.pdf",
                "id": "fake_resource_id",
                "format": "",
            },
            {"url": "http://example.com", "format": ""},
            {"url": "my.csv", "format": ""}
        ],
    }
    data = df.flatten_dict(data)

    @t.does_not_modify_errors_dict
    def call_validator(*args, **kwargs):
        return validators.if_empty_guess_format(*args, **kwargs)

    new_data = copy.deepcopy(data)
    call_validator(
        key=("resources", 0, "format"), data=new_data, errors={}, context={}
    )
    assert new_data[("resources", 0, "format")] == "text/csv"

    new_data = copy.deepcopy(data)
    call_validator(
        key=("resources", 1, "format"), data=new_data, errors={}, context={}
    )
    assert new_data[("resources", 1, "format")] == "application/pdf"

    new_data = copy.deepcopy(data)
    call_validator(
        key=("resources", 2, "format"), data=new_data, errors={}, context={}
    )
    assert new_data[("resources", 2, "format")] == "pdf"

    new_data = copy.deepcopy(data)
    call_validator(
        key=("resources", 3, "format"), data=new_data, errors={}, context={}
    )
    assert new_data[("resources", 3, "format")] == ""

    new_data = copy.deepcopy(data)
    call_validator(
        key=("resources", 4, "format"), data=new_data, errors={}, context={}
    )
    assert new_data[("resources", 4, "format")] == ""

    new_data = copy.deepcopy(data)
    call_validator(
        key=("resources", 5, "format"), data=new_data, errors={}, context={}
    )
    assert new_data[("resources", 5, "format")] == "text/csv"


def test_clean_format():
    format = validators.clean_format("csv")
    assert format == "CSV"

    format = validators.clean_format("text/csv")
    assert format == "CSV"

    format = validators.clean_format("not a format")
    assert format == "not a format"

    format = validators.clean_format("")
    assert format == ""


def test_datasets_with_org_can_be_private_when_creating():
    data = factories.validator_data_dict()
    errors = factories.validator_errors_dict()

    key = ("private",)
    data[key] = True
    errors[key] = []

    data[("owner_org",)] = "some_org_id"

    # Mock ckan.model.
    mock_model = mock.MagicMock()

    @t.does_not_modify_errors_dict
    @t.does_not_modify_data_dict
    @t.returns_None
    def call_validator(*args, **kwargs):
        return validators.datasets_with_no_organization_cannot_be_private(
            *args, **kwargs
        )

    call_validator(key, data, errors, context={"model": mock_model})


def test_datasets_with_no_org_cannot_be_private_when_creating():
    data = factories.validator_data_dict()
    errors = factories.validator_errors_dict()

    key = ("private",)
    data[key] = True
    errors[key] = []

    # Mock ckan.model.
    mock_model = mock.MagicMock()

    @t.does_not_modify_data_dict
    @adds_message_to_errors_dict(
        "Datasets with no organization can't be private."
    )
    def call_validator(*args, **kwargs):
        return validators.datasets_with_no_organization_cannot_be_private(
            *args, **kwargs
        )

    call_validator(key, data, errors, context={"model": mock_model})


def test_datasets_with_org_can_be_private_when_updating():
    data = factories.validator_data_dict()
    errors = factories.validator_errors_dict()

    key = ("private",)
    data[key] = True
    errors[key] = []

    data[("id",)] = "some_dataset_id"
    data[("owner_org",)] = "some_org_id"

    # Mock ckan.model.
    mock_model = mock.MagicMock()

    @t.does_not_modify_errors_dict
    @t.does_not_modify_data_dict
    @t.returns_None
    def call_validator(*args, **kwargs):
        return validators.datasets_with_no_organization_cannot_be_private(
            *args, **kwargs
        )

    call_validator(key, data, errors, context={"model": mock_model})


def test_int_unchanged():
    returns_arg(validators.int_validator)(42)


def test_zero_unchanged():
    returns_arg(validators.int_validator)(0)


def test_long_unchanged():
    returns_arg(validators.int_validator)(3948756923874659827346598)


def test_None_unchanged():
    returns_arg(validators.int_validator)(None)


def test_float_converted():
    assert validators.int_validator(42.0, None) == 42


def test_fraction_converted():
    assert validators.int_validator(fractions.Fraction(2, 1), {}) == 2


def test_decimal_converted():
    assert validators.int_validator(decimal.Decimal("19.00"), {}) == 19


def test_long_int_string_converted():
    assert (
        validators.int_validator("528735648764587235684376", {})
        == 528735648764587235684376
    )


def test_negative_int_string_converted():
    assert validators.int_validator("-2", {}) == -2


def test_positive_int_string_converted():
    assert validators.int_validator("+3", {}) == 3


def test_zero_prefixed_int_string_converted_as_decimal():
    assert validators.int_validator("0123", {}) == 123


def test_string_with_whitespace_converted():
    assert validators.int_validator("\t  98\n", {}) == 98


def test_empty_string_becomes_None():
    assert validators.int_validator("", {}) is None


def test_whitespace_string_becomes_None():
    assert validators.int_validator("\n\n  \t", {}) is None


def test_float_with_decimal_raises_Invalid():
    raises_Invalid(validators.int_validator)(42.5, {})


def test_float_string_raises_Invalid():
    raises_Invalid(validators.int_validator)("42.0", {})


def test_exponent_string_raises_Invalid():
    raises_Invalid(validators.int_validator)("1e6", {})


def test_non_numeric_string_raises_Invalid():
    raises_Invalid(validators.int_validator)("text", {})


def test_non_whole_fraction_raises_Invalid():
    raises_Invalid(validators.int_validator)(fractions.Fraction(3, 2), {})


def test_non_whole_decimal_raises_Invalid():
    raises_Invalid(validators.int_validator)(decimal.Decimal("19.99"), {})


def test_complex_with_imaginary_component_raises_Invalid():
    with warnings.catch_warnings():  # divmod() issues warning for complex
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        raises_Invalid(validators.int_validator)(1 + 1j, {})


def test_complex_without_imaginary_component_raises_Invalid():
    with warnings.catch_warnings():  # divmod() issues warning for complex
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        raises_Invalid(validators.int_validator)(1 + 0j, {})


def test_bool_true():
    assert validators.boolean_validator(True, None)


def test_bool_false():
    assert not validators.boolean_validator(False, None)


def test_missing():
    assert not validators.boolean_validator("", None)


def test_none():
    assert not validators.boolean_validator(None, None)


def test_string_true():
    assert validators.boolean_validator("true", None)
    assert validators.boolean_validator("yes", None)
    assert validators.boolean_validator("t", None)
    assert validators.boolean_validator("y", None)
    assert validators.boolean_validator("1", None)


def test_string_false():
    assert not validators.boolean_validator("f", None)


def _make_context():
    return {"model": model, "session": model.Session}


def test_package_name_exists_empty():
    with pytest.raises(df.Invalid):
        validators.package_name_exists("", _make_context())


@pytest.mark.usefixtures("clean_db")
def test_package_name_exists():
    name = "pne_validation_test"
    dataset = factories.Dataset(name=name)
    v = validators.package_name_exists(name, _make_context())
    assert v == name


def test_resource_id_exists_empty():
    with pytest.raises(df.Invalid):
        validators.resource_id_exists("", _make_context())


@pytest.mark.usefixtures("clean_db")
def test_resource_id_exists():
    resource = factories.Resource()
    v = validators.resource_id_exists(resource["id"], _make_context())
    assert v == resource["id"]


def test_user_id_or_name_exists_empty():
    with pytest.raises(df.Invalid):
        validators.user_id_or_name_exists("", _make_context())


@pytest.mark.usefixtures("clean_db", "with_request_context")
def test_user_id_or_name_exists():
    user = factories.User(name="username")
    v = validators.user_id_or_name_exists(user["id"], _make_context())
    assert v == user["id"]
    v = validators.user_id_or_name_exists(user["name"], _make_context())
    assert v == user["name"]


def test_group_id_or_name_exists_empty():
    with pytest.raises(df.Invalid):
        validators.user_id_or_name_exists("", _make_context())


@pytest.mark.usefixtures("clean_db", "with_request_context")
def test_group_id_or_name_exists():
    group = factories.Group()
    v = validators.group_id_or_name_exists(group["id"], _make_context())
    assert v == group["id"]

    v = validators.group_id_or_name_exists(group["name"], _make_context())
    assert v == group["name"]


def test_role_exists_empty():
    with pytest.raises(df.Invalid):
        validators.role_exists("", _make_context())


def test_password_ok():
    passwords = ["MyPassword1", "my1Password", "1PasswordMY"]
    key = ("password",)

    @t.does_not_modify_errors_dict
    def call_validator(*args, **kwargs):
        return validators.user_password_validator(*args, **kwargs)

    for password in passwords:
        errors = factories.validator_errors_dict()
        errors[key] = []
        call_validator(key, {key: password}, errors, None)


def test_password_too_short():
    password = "MyPass1"
    key = ("password",)

    @adds_message_to_errors_dict(
        "Your password must be 8 characters or " "longer"
    )
    def call_validator(*args, **kwargs):
        return validators.user_password_validator(*args, **kwargs)

    errors = factories.validator_errors_dict()
    errors[key] = []
    call_validator(key, {key: password}, errors, None)


def test_url_ok():
    urls = [
        "http://example.com",
        "https://example.com",
        "https://example.com/path?test=1&key=2",
    ]
    key = ("url",)

    @t.does_not_modify_errors_dict
    def call_validator(*args, **kwargs):
        return validators.url_validator(*args, **kwargs)

    for url in urls:
        errors = factories.validator_errors_dict()
        errors[key] = []
        call_validator(key, {key: url}, errors, None)


def test_url_invalid():
    urls = ["ftp://example.com", "test123", "https://example.com]"]
    key = ("url",)

    @adds_message_to_errors_dict("Please provide a valid URL")
    def call_validator(*args, **kwargs):
        return validators.url_validator(*args, **kwargs)

    for url in urls:
        errors = factories.validator_errors_dict()
        errors[key] = []
        call_validator(key, {key: url}, errors, None)


class TestOneOfValidator(object):
    def test_val_in_list(self):
        cont = [1, 2, 3, 4]
        func = validators.one_of(cont)
        assert func(1) == 1

    def test_val_not_in_list(self):
        cont = [1, 2, 3, 4]
        func = validators.one_of(cont)
        raises_Invalid(func)(5)

    def test_empty_val_accepted(self):
        cont = [1, 2, 3, 4]
        func = validators.one_of(cont)
        assert func("") == ""
