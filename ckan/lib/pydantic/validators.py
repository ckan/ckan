def pydantic_not_empty(value, values, config, field):
    """Ensure value is available in the input and is not empty."""
    breakpoint()
    valid_values = [False, 0, 0.0]

    if value in valid_values:
        return value

    if not value:
        raise ValueError(f"Missing {field.name}")
    return value


def pydantic_user_password_validator(value, values, config, field):
    """Ensures that password is safe enough."""
    breakpoint()

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, str):
        raise ValueError("Passwords must be strings")
    elif value == "":
        pass
    elif len(value) < 8:
        raise ValueError("Your password must be 8 characters or longer")
    return value


def pydantic_user_passwords_match(value, values, config, field):
    """Ensures that password and password confirmation match."""
    breakpoint()
    if field.name == "password2":
        if not value == values["password1"]:
            raise ValueError("The passwords you entered do not match")
        else:
            # Set correct password
            values["password"] = value
        return value
