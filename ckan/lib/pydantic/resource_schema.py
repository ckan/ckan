import datetime
import pydantic
from typing import Any, Optional
from ckan.lib.pydantic.base import CKANBaseModel


uuidv4_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
class DefaultResourceSchema(CKANBaseModel):

    id: Optional[str] = pydantic.Field(
        None, min_length=7, max_length=100, regex=uuidv4_pattern
    )
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

    _validators = {
        'id': ["p_ignore_empty", "unicode_safe"],
        'package_id': ["p_ignore"],
        'url': ["p_ignore_missing", "unicode_safe", "remove_whitespace"],
        'description': ["p_ignore_missing", "unicode_safe"],
        'format': ["if_empty_guess_format", "p_ignore_missing", "clean_format",
                   "unicode_safe"],
        'hash': ["p_ignore_missing", "unicode_safe"],
        'state': ["p_ignore"],
        'position': ["p_ignore"],
        'name': ["p_ignore_missing", "unicode_safe"],
        'resource_type': ["p_ignore_missing", "unicode_safe"],
        'url_type': ["p_ignore_missing", "unicode_safe"],
        'mimetype': ["p_ignore_missing", "unicode_safe"],
        'mimetype_inner': ["p_ignore_missing", "unicode_safe"],
        'cache_url': ["p_ignore_missing", "unicode_safe"],
        'size': ["p_ignore_missing", "int_validator"],
        'created': ["p_ignore_missing", "isodate"],
        'last_modified': ["p_ignore_missing", "isodate"],
        'cache_last_updated': ["p_ignore_missing", "isodate"],
        'tracking_summary': ["p_ignore_missing"],
        'datastore_active': ["p_ignore_missing"],
        '_extras': ["p_ignore_missing", "extras_valid_json", "keep_extras"],
    }


class DefaultResourceUpdateSchema(DefaultResourceSchema):
    pass
