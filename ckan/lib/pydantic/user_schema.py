import pydantic
from pydantic.fields import ModelField
from pydantic.class_validators import Validator

from typing import Optional, Any, Dict, List, Callable

import ckan.lib.navl.dictization_functions as df
from ckan.plugins.toolkit import _


Missing = df.Missing
StopOnError = df.StopOnError


def not_empty(value, values, config, field):
    """Ensure value is available in the input and is not empty."""
    breakpoint()
    valid_values = [False, 0, 0.0]

    if value in valid_values:
        return value

    if not value:
        raise ValueError(f"Missing {field.name}")
    return value


def user_password_validator(value, values, config, field) -> Any:
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


def user_passwords_match(
    value: str, values: "dict[str, Any]", config, field
) -> Any:
    """Ensures that password and password confirmation match."""
    breakpoint()
    if field.name == "password2":
        if not value == values["password1"]:
            raise ValueError("The passwords you entered do not match")
        else:
            # Set correct password
            values["password"] = value
        return value


not_empty_ = Validator(not_empty)
user_password_validator_ = Validator(user_password_validator)


class CKANModel(pydantic.BaseModel):

    @classmethod
    def add_fields(cls, field_definitions: List[Dict[str, Any]]) -> None:

        for field_definition in field_definitions:
            new_fields: Dict[str, ModelField] = {}
            new_annotations: Dict[str, Optional[type]] = {}
            class_validators: Dict[str, Callable[..., Any]] = {}

            f_name = field_definition['name']
            type_ = field_definition.get('type')
            extra = field_definition.get('extra')

            if isinstance(type_, tuple):
                try:
                    f_annotation, f_value = type_
                except ValueError as e:
                    raise Exception(
                        'field definitions should be a tuple of (<type>, <default>)'
                    ) from e
            else:
                f_annotation, f_value = None, type_

            if f_annotation:
                new_annotations[f_name] = f_annotation

            if extra:
                class_validators.update(extra)

            new_fields[f_name] = ModelField.infer(name=f_name, value=f_value, annotation=f_annotation, class_validators=class_validators, config=cls.__config__)
            cls.schema().update({f_name: {'title': f_name.capitalize(), 'type': new_annotations[f_name]}})

            cls.__fields__.update(new_fields)
            cls.__annotations__.update(new_annotations)

    @classmethod
    def update_fields(cls, field_definitions: List[Dict[str, Any]]) -> None:
        for field_definition in field_definitions:
            validator = field_definition.get('extra')
            breakpoint()
            if validator:
                f = cls.__fields__[field_definition['name']]
                f.class_validators.update(validator)
                f.populate_validators()

    def __init_subclass__(cls):
        for name, f in cls.__fields__.items():
            if 'extra' in cls.schema()['properties'][name]:
                validators = cls.schema()['properties'][name]['extra']
                f.class_validators.update(validators)
            # f.prepare()
            f.populate_validators()


class UserCreateSchema(CKANModel):
    name: str = pydantic.Field(None, extra={'not_empty': not_empty_})
    email: str
    password: Optional[str]
    password1: pydantic.constr(strip_whitespace=True, min_length=8)  # type: ignore
    password2: pydantic.constr(strip_whitespace=True, min_length=8)  # type: ignore
    fullname: Optional[str] = None
    apikey: Optional[str] = None

    class Config:
        extra = "allow"

    # _not_empty = pydantic.validator("name", "email", check_fields=True)(
    #     not_empty
    # )
    # _user_password_validator = pydantic.validator("password2")(
    #     user_password_validator
    # )
    # _user_passwords_match = pydantic.validator("password2")(
    #     user_passwords_match
    # )


# this is for reference only 
# in the same way, we can update the schema from the plugins by adding new fields
UserCreateSchema.add_fields([
    # Elipsis means the field is Required!
    # it also can be None, this means the field is Optional[type]
    # or set it to default value e.g (str, 'defaul_value')
    {'name': 'buz', 'type': (str, ...), 'title': 'Buz', 'extra': {'validator': not_empty_}},
    {'name': 'foo', 'type': (str, None), 'title': 'Foo', 'extra': {'validator': not_empty_}}
])
