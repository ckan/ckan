import datetime
import pydantic
from typing import Any, Optional


class DefaultResourceSchema(pydantic.BaseModel):

    id: Optional[str]
    package_id: Optional[str]
    url: Optional[str]
    description: Optional[str]
    format: Optional[str]
    hash: Optional[str]
    state: Optional[str]
    position: Optional[str]
    name: Optional[str]
    resource_type: Optional[str]
    url_type: Optional[str]
    mimetype: Optional[str]
    mimetype_inner: Optional[str]
    cache_url: Optional[str]
    size: Optional[int]
    created: Optional[datetime.datetime]
    last_modified: Optional[datetime.datetime]
    cache_last_updated: Optional[datetime.datetime]
    tracking_summary: Optional[str]
    datastore_active: Optional[str]
    _extras: Optional["list[dict[str, Any]]"]


class DefaultResourceUpdateSchema(DefaultResourceSchema):
    pass
