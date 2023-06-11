import pydantic
from typing import Optional

from ckan.lib.pydantic.base import CKANBaseModel


class UserCreateSchema(CKANBaseModel):
    name: str
    email: str
    password: Optional[str]
    password1 = pydantic.constr(strip_whitespace=True, min_length=8)
    password2 = pydantic.constr(strip_whitespace=True, min_length=8)
    fullname: Optional[str] = None
    apikey: Optional[str] = None
