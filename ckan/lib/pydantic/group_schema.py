import pydantic
from typing import Optional, List, Any
from typing_extensions import Literal

from .mixed_schema import DefaultExtrasSchema
from .dataset_schema import DefaultShowPackageSchema
from .user_schema import UserCreateSchema


class DefaultGroupSchema(pydantic.BaseModel):
    id: Optional[str]
    name: str
    title: Optional[str]
    description: Optional[str]
    image_url:  Optional[str]
    image_display_url: Optional[str]
    type: Optional[str]
    state: Optional[str]
    _created: Optional[str]
    is_organization: Optional[str]
    approval_status: Optional[str]
    extras: Optional[List[DefaultExtrasSchema]]
    _extras: Literal[None]
    _junk: Literal[None]
    packages: Optional[List[DefaultShowPackageSchema]]
    users: Optional[List[UserCreateSchema]]
    groups: Optional[List["dict[str, Any]"]]


class GroupFormSchema(DefaultGroupSchema):
    pass


class DefaultUpdateGroupSchema(DefaultGroupSchema):
    name: Optional[str]  # type: ignore
