import inspect
import pydantic

from pydantic.fields import ModelField
from typing import Optional, Any, Dict, List

import ckan.lib.navl.dictization_functions as df
import ckan.logic as logic

from ckan.types import Context
from ckan.logic import get_validator
from ckan.config.declaration.option import _validators_from_string


Invalid = df.Invalid
StopOnError = df.StopOnError
ValidationError = logic.ValidationError


class CKANBaseModel(pydantic.BaseModel):
    """
    Base class for all pydantic models.
    """

    _validators = {}

    class Config:
        # allow extra attributes during model initialisation.
        extra = "allow"
        # allow arbitrary user types for fields
        arbitrary_types_allowed = True
        # strip leading and trailing whitespace for str & byte types
        anystr_strip_whitespace = True
        # validate field defaults
        validate_all = True

        context: Context = {}

    @classmethod
    def add_fields(cls, field_definitions: List[Dict[str, Any]]) -> None:
        """Add fields to the model based on the provided field definitions.

        :field_definitions: A list of dictionaries containing field definitions.

        :Example:

            field_definitions = [
                {'name': 'title', 'type': (str, ...)},
                {'name': 'age', 'type': (int, None), 'extra': ['pydantic_validators']},
            ]
            AnyPydanticModel.add_fields(field_definitions)

        :Returns: None
        """
        for field_definition in field_definitions:
            new_fields: Dict[str, ModelField] = {}
            new_annotations: Dict[str, Optional[type]] = {}

            f_name = field_definition["name"]
            type_ = field_definition.get("type")
            extra_validators = field_definition.get("extra")

            if isinstance(type_, tuple):
                try:
                    f_annotation, f_value = type_
                except ValueError as e:
                    raise Exception(
                        "field definitions should be a tuple of (<type>,"
                        " <default>)"
                    ) from e
            else:
                f_annotation, f_value = None, type_

            if f_annotation:
                new_annotations[f_name] = f_annotation

            if extra_validators:
                cls._validators[f_name] = extra_validators

            new_fields[f_name] = ModelField.infer(
                name=f_name,
                value=f_value,
                annotation=f_annotation,
                class_validators={},
                config=cls.__config__,
            )
            cls.__fields__.update(new_fields)
            cls.__annotations__.update(new_annotations)

    @classmethod
    def add_validators(cls, field_names: Dict[str, Any]) -> None:
        """Add validators to the model based on the provided field names.

        :param field_names: A dictionary containing field names as keys and validator functions as values.

        :Example:

            field_names = {
                'name': ['validate_name', 'pydantic_not_empty'],
                'email': ['validate_email'],
            }
            AnyPydanticModel.add_validators(field_names)

        :Returns: None

        :Raises: ValueError: If the field name is not found in the model.
        """
        for f_name, validator_func in field_names.items():
            if f_name in cls.__fields__:
                cls._validators[f_name] = validator_func
            else:
                raise ValueError(
                    f"Field name {f_name} not found in {cls.__name__}"
                )

    @pydantic.root_validator(pre=True)
    def validate_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        context = cls.Config.context
        errors = {}

        for name, _ in cls.__fields__.items():
            errors[name] = []

            extra_validators = cls._validators.get(name)
            if extra_validators:
                for validator_func in extra_validators:
                    if not isinstance(validator_func, str):
                        continue

                    try:
                        _validate(validator_func, name, values, cls, context)
                    except (ValueError, Invalid) as e:
                        errors[name].append(e.args[0])
                        break
                    except StopOnError:
                        break

            if not errors[name]:
                del errors[name]

        if errors:
            raise ValidationError(errors)
        return values


def _validate(
    validator_func: str,
    field_name: str,
    values: Dict[str, Any],
    model: CKANBaseModel,
    context: Context,
) -> Any:

    value = {}
    if '(' in validator_func:
        v = _validators_from_string(validator_func)
        if v:
            v = v[0]
            v(
            values.get(field_name), 
            values,  # type: ignore
            model.__config__,  # type: ignore
            model.__fields__[field_name], 
            context)  # type: ignore

    else:
        validator = get_validator(validator_func)
        # get the function signature
        signature = inspect.signature(validator)
        # get the length
        parameters_length = len(signature.parameters)

        # functions like unicode_safe expect only one argument
        # so there is no need to rewrite it as a pydantic_validator
        if parameters_length == 1:
            value = validator(values.get(field_name, ""))  # type: ignore
        # functions like package_id_does_not_exist expect two arguments
        # so there is no need to rewrite it as a pydantic_validator
        elif parameters_length == 2:
            value = validator(values.get(field_name, ""), context)  # type: ignore
        # pydantic custom validators expect 5 arguments
        elif parameters_length == 5:
            value = validator(
                values.get(field_name),
                values,  # type: ignore
                model.__config__,  # type: ignore
                model.__fields__[field_name],
                context,  # type: ignore
            )
    return value
