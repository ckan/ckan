# encoding: utf-8

from typing import Any, Callable, NoReturn
import six


import ckan.lib.navl.dictization_functions as df

from ckan.common import _, json, config
from ckan.types import (
    Context, FlattenDataDict, FlattenErrorDict, FlattenKey, Validator
)

missing = df.missing
StopOnError = df.StopOnError
Invalid = df.Invalid


def keep_extras(key: FlattenKey, data: FlattenDataDict,
                errors: FlattenErrorDict, context: Context) -> None:
    """Convert dictionary into simple fields.

    .. code-block::

        data, errors = tk.navl_validate(
            {"input": {"hello": 1, "world": 2}},
            {"input": [keep_extras]}
        )
        assert data == {"hello": 1, "world": 2}

    """
    extras = data.pop(key, {})
    for extras_key, value in extras.items():
        data[key[:-1] + (extras_key,)] = value


def not_missing(key: FlattenKey, data: FlattenDataDict,
                errors: FlattenErrorDict, context: Context) -> None:
    """Ensure value is not missing from the input, but may be empty.

    .. code-block::

        data, errors = tk.navl_validate(
            {},
            {"hello": [not_missing]}
        )
        assert errors == {"hello": [error_message]}

    """
    value = data.get(key)
    if value is missing:
        errors[key].append(_('Missing value'))
        raise StopOnError


def not_empty(key: FlattenKey, data: FlattenDataDict,
              errors: FlattenErrorDict, context: Context) -> None:
    """Ensure value is available in the input and is not empty.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": None},
            {"hello": [not_empty]}
        )
        assert errors == {"hello": [error_message]}

    """
    value = data.get(key)
    valid_values = [False, 0, 0.0]

    if value in valid_values:
        return

    if value is missing or not value:
        errors[key].append(_('Missing value'))
        raise StopOnError

def if_empty_same_as(other_key: str) -> Callable[..., Any]:
    """Copy value from other field when current field is missing or empty.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": 1},
            {"hello": [], "world": [if_empty_same_as("hello")]}
        )
        assert data == {"hello": 1, "world": 1}

    """
    def callable(key: FlattenKey, data: FlattenDataDict,
                 errors: FlattenErrorDict, context: Context):
        value = data.get(key)
        if not value or value is missing:
            data[key] = data[key[:-1] + (other_key,)]

    return callable


def both_not_empty(other_key: str) -> Validator:
    """Ensure that both, current value and other field has value.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": 1},
            {"hello": [], "world": [both_not_empty("hello")]}
        )
        assert errors == {"world": [error_message]}

        data, errors = tk.navl_validate(
            {"world": 1},
            {"hello": [], "world": [both_not_empty("hello")]}
        )
        assert errors == {"world": [error_message]}

        data, errors = tk.navl_validate(
            {"hello": 1, "world": 2},
            {"hello": [], "world": [both_not_empty("hello")]}
        )
        assert not errors

    """
    def callable(key: FlattenKey, data: FlattenDataDict,
                 errors: FlattenErrorDict, context: Context):
        value = data.get(key)
        other_value = data.get(key[:-1] + (other_key,))

        if (not value or value is missing and
            not other_value or other_value is missing):
            errors[key].append(_('Missing value'))
            raise StopOnError

    return callable


def empty(key: FlattenKey, data: FlattenDataDict,
          errors: FlattenErrorDict, context: Context) -> None:
    """Ensure that value is not present in the input.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": 1},
            {"hello": [empty]}
        )
        assert errors == {"hello": [error_message]}

    """

    value = data.pop(key, None)

    if value and value is not missing:
        key_name = key[-1]
        if key_name == '__junk':
            # for junked fields, the field name is contained in the value
            key_name = list(value.keys())
        errors[key].append(_(
            'The input field %(name)s was not expected.') % {"name": key_name})


def ignore(key: FlattenKey, data: FlattenDataDict,
           errors: FlattenErrorDict, context: Context) -> NoReturn:
    """Remove the value from the input and skip the rest of validators.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": 1},
            {"hello": [ignore]}
        )
        assert data == {}

    """
    data.pop(key, None)
    raise StopOnError

def default(default_value: Any) -> Validator:
    """Convert missing or empty value to the default one.

    .. code-block::

        data, errors = tk.navl_validate(
            {},
            {"hello": [default("not empty")]}
        )
        assert data == {"hello": "not empty"}

    """

    def callable(key: FlattenKey, data: FlattenDataDict,
                 errors: FlattenErrorDict, context: Context):

        value = data.get(key)
        if value is None or value == '' or value is missing:
            data[key] = default_value

    return callable


def configured_default(config_name: str,
                       default_value_if_not_configured: Any) -> Validator:
    '''When key is missing or value is an empty string or None, replace it with
    a default value from config, or if that isn't set from the
    default_value_if_not_configured.'''

    default_value = config.get(config_name)
    if default_value is None:
        default_value = default_value_if_not_configured
    return default(default_value)


def ignore_missing(key: FlattenKey, data: FlattenDataDict,
                   errors: FlattenErrorDict, context: Context) -> None:
    '''If the key is missing from the data, ignore the rest of the key's
    schema.

    By putting ignore_missing at the start of the schema list for a key,
    you can allow users to post a dict without the key and the dict will pass
    validation. But if they post a dict that does contain the key, then any
    validators after ignore_missing in the key's schema list will be applied.

    :raises ckan.lib.navl.dictization_functions.StopOnError: if ``data[key]``
        is :py:data:`ckan.lib.navl.dictization_functions.missing` or ``None``

    :returns: ``None``

    '''
    value = data.get(key)

    if value is missing or value is None:
        data.pop(key, None)
        raise StopOnError


def ignore_empty(key: FlattenKey, data: FlattenDataDict,
                 errors: FlattenErrorDict, context: Context) -> None:
    """Skip the rest of validators if the value is empty or missing.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": ""},
            {"hello": [ignore_empty, isodate]}
        )
        assert data == {}
        assert not errors

    """
    value = data.get(key)

    if value is missing or not value:
        data.pop(key, None)
        raise StopOnError

def convert_int(value: Any) -> int:
    """Ensure that the value is a valid integer.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": "world"},
            {"hello": [convert_int]}
        )
        assert errors == {"hello": [error_message]}

    """
    try:
        return int(value)
    except ValueError:
        raise Invalid(_('Please enter an integer value'))

def unicode_only(value: Any) -> str:
    '''Accept only unicode values

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": 1},
            {"hello": [unicode_only]}
        )
        assert errors == {"hello": [error_message]}

    '''

    if not isinstance(value, str):
        raise Invalid(_('Must be a Unicode string value'))
    return value

def unicode_safe(value: Any) -> str:
    '''
    Make sure value passed is treated as unicode, but don't raise
    an error if it's not, just make a reasonable attempt to
    convert other types passed.

    This validator is a safer alternative to the old ckan idiom
    of using the unicode() function as a validator. It tries
    not to pollute values with Python repr garbage e.g. when passed
    a list of strings (uses json format instead). It also
    converts binary strings assuming either UTF-8 or CP1252
    encodings (not ASCII, with occasional decoding errors)
    '''
    if isinstance(value, str):
        return value
    if hasattr(value, 'filename'):
        # cgi.FieldStorage instance for uploaded files, show the name
        value = value.filename
    if value is missing or value is None:
        return u''
    if isinstance(value, bytes):
        # bytes only arrive when core ckan or plugins call
        # actions from Python code
        try:
            return six.ensure_text(value)
        except UnicodeDecodeError:
            return value.decode(u'cp1252')
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    except Exception:
        # at this point we have given up. Just don't error out
        try:
            return str(value)
        except Exception:
            return u'\N{REPLACEMENT CHARACTER}'


def limit_to_configured_maximum(config_option: str,
                                default_limit: int) -> Validator:
    '''
    If the value is over a limit, it changes it to the limit. The limit is
    defined by a configuration option, or if that is not set, a given int
    default_limit.
    '''
    def callable(value: Any):
        value = convert_int(value)
        limit = int(config.get(config_option, default_limit))
        if value > limit:
            return limit
        return value

    return callable
