import pydantic
from typing import Optional, Any

import ckan.lib.navl.dictization_functions as df


Missing = df.Missing


def not_empty(value, values, config, field) -> None:
    """Ensure value is available in the input and is not empty.
    """
    breakpoint()
    valid_values = [False, 0, 0.0]

    if value in valid_values:
        return

    if not value:
        raise ValueError(f'Missing {field.name}')
    return value


def user_password_validator(value, values, config, field) -> Any:
    """Ensures that password is safe enough.
    """
    breakpoint()

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, str):
        raise ValueError('Passwords must be strings')
    elif value == '':
        pass
    elif len(value) < 8:
        raise ValueError('Your password must be 8 characters or '
                                       'longer')
    return value

def user_passwords_match(value, values, config, field) -> Any:
    """Ensures that password and password confirmation match.
    """
    breakpoint()
    if field.name == 'password2':

        if not value == values['password1']:
            raise ValueError('The passwords you entered do not match')
        else:
            #Set correct password
            values['password'] = value
        return value


class UserCreateSchema(pydantic.BaseModel):

    name: str
    email: str
    password: Optional[str]
    password1: pydantic.constr(strip_whitespace=True, min_length=8)
    password2: str
    fullname: Optional[str]
    apikey: Optional[str]

    class Config:
        extra = "allow"

    _not_empty = pydantic.validator('name', 'email', check_fields=True)(not_empty)
    _user_password_validator = pydantic.validator('password2')(user_password_validator)
    _user_passwords_match = pydantic.validator('password2')(user_passwords_match)
