
import pydantic
import ckan.logic as logic

from typing import Type, Set, Optional
from ckan.types import Context, DataDict, Union
from ckan.lib.pydantic.base import CKANBaseModel


def validate_with_pydantic(  # type: ignore
    data_dict: DataDict,
    schema: Type[CKANBaseModel], 
    context: Context,
    include: Union[Set[str], None] = None,
    exclude: Union[Set[str], None] = None,
    by_alias: bool = False,
    skip_defaults: Optional[bool] = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = True,
):
    schema.Config.context = context

    position = None
    old_data_dict = data_dict
    breakpoint()
    if context.get('resource_to_validate', None):
        validators = schema._validators['resources']
        for val in validators:
            if isinstance(val, type) and issubclass(val, CKANBaseModel):
                schema = val
                break
        data_dict, position = context.pop('resource_to_validate')

    if exclude is None:
        exclude = {'_ckan_phase', 'pkg_name'}

    try:
        model_instance = schema(**data_dict)
    except logic.ValidationError as e:
        return {}, e.error_dict
    except pydantic.error_wrappers.ValidationError as e:
        return {}, e.errors()

    result = model_instance.dict(
        include=include,
        exclude=exclude,
        by_alias=by_alias,
        skip_defaults=skip_defaults,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
    )

    if position:
        old_data_dict['resources'][position] = result
        result = old_data_dict

    return result, {}
