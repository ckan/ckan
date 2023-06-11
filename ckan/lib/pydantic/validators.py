from pydantic import BaseConfig
from pydantic.fields import ModelField
from typing import Any, Dict, Type, Union, Optional

import ckan.lib.navl.dictization_functions as df
from ckan.types import Context
from ckan.model.core import State
from ckan.common import _
from ckan.model import PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH


Missing = df.Missing
missing = df.missing
Invalid = df.Invalid
StopOnError = df.StopOnError


def pydantic_not_empty(
    value: Any,
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
):
    """Ensure value is available in the input and is not empty."""

    valid_values = [False, 0, 0.0]

    if value in valid_values:
        return value

    if not value:
        raise ValueError(f"Missing {field.name}")
    return value


def pydantic_user_password_validator(
    value: Any,
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
):
    """Ensures that password is safe enough."""

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, str):
        raise ValueError("Passwords must be strings")
    elif value == "":
        pass
    elif len(value) < 8:
        raise ValueError("Your password must be 8 characters or longer")
    return value


def pydantic_user_passwords_match(
    value: Any,
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
):
    """Ensures that password and password confirmation match."""

    if field.name == "password2":
        if not value == values["password1"]:
            raise ValueError("The passwords you entered do not match")
        else:
            # Set correct password
            values["password"] = value
        return value


def pydantic_empty_if_not_sysadmin(
    value: Any,
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
):
    '''Only sysadmins may pass this value'''
    from ckan.common import current_user

    ignore_auth = context.get('ignore_auth')
    if current_user.is_authenticated:
        if ignore_auth or current_user.sysadmin:  # type: ignore
            return value

    if value:
        raise ValueError('The input field %(name)s was not expected.' % {"name": field.name})


def pydantic_package_name_validator(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> Any:
    """Ensures that value can be used as a package's name
    """
    model = context['model']
    session = context['session']
    package = context.get('package')

    query = session.query(model.Package.id).filter(
        model.Package.name == value,
        model.Package.state != State.DELETED,
    )
    if package:
        package_id: Union[Optional[str], Missing] = package.id
    else:
        package_id = value
    if package_id and package_id is not missing:
        query = query.filter(model.Package.id != package_id)

    if session.query(query.exists()).scalar():
        raise Invalid(_('That URL is already in use.'))

    if len(value) < PACKAGE_NAME_MIN_LENGTH:
        raise Invalid(
            _('Name "%s" length is less than minimum %s') % (value, PACKAGE_NAME_MIN_LENGTH)
        )
    if len(value) > PACKAGE_NAME_MAX_LENGTH:
        raise Invalid(
            _('Name "%s" length is more than maximum %s') % (value, PACKAGE_NAME_MAX_LENGTH)
        )


def pydantic_ignore_missing(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> None:
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

    if value is missing or value is None:
        values.pop(value, None)
        raise StopOnError
