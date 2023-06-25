from typing import  Optional

import ckan.model as model
from ckan.logic.validators import one_of
from ckan.lib.pydantic.base import CKANBaseModel


class DefaultExtrasSchema(CKANBaseModel):

    _validators = {}

    _id: Optional[str]
    key: Optional[str]
    value: Optional[str]
    state: Optional[str]
    _delete: Optional[str]
    _revision_timestamp: Optional[str]


class DefaultRelationshipSchema(CKANBaseModel):

    _validators = {}

    id: Optional[str]
    subject: Optional[str]
    object: Optional[str]
    type: str = one_of(model.PackageRelationship.get_all_types()) # type: ignore
    comment: Optional[str]
    _state: Optional[str]
