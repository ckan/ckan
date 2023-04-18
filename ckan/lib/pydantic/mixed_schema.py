import pydantic
from typing import  Optional

import ckan.model as model
from ckan.logic.validators import one_of


class DefaultExtrasSchema(pydantic.BaseModel):
    _id: Optional[str]
    key: str = ''
    value: str = ''
    state: Optional[str]
    _delete: Optional[str]
    _revision_timestamp: Optional[str]


class DefaultRelationshipSchema(pydantic.BaseModel):
    id: Optional[str]
    subject: Optional[str]
    object: Optional[str]
    type: str = one_of(model.PackageRelationship.get_all_types()) # type: ignore
    comment: Optional[str]
    _state: Optional[str]
