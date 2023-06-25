import pydantic
from typing import Any, Optional
from ckan.lib.pydantic.base import CKANBaseModel


uuidv4_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
class DefaultResourceSchema(CKANBaseModel):

    id: Optional[str] = pydantic.Field(regex=uuidv4_pattern)
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
    size: Optional[str]
    created: Optional[str]
    last_modified: Optional[str]
    cache_last_updated: Optional[str]
    tracking_summary: Optional["dict[str, Any]"]
    datastore_active: Optional[bool]
    _extras: Optional["list[dict[str, Any]]"]

    _validators = {
        'id': ["p_ignore_empty", "p_resource_id_does_not_exist", "unicode_safe"],
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
        '_extras': ["p_ignore_missing", "extras_valid_json", "p_keep_extras"],
    }


class DefaultResourceUpdateSchema(DefaultResourceSchema):
    pass


class DefaultResourceForPackageShow(DefaultResourceSchema):

    _validators = {
        **DefaultResourceSchema._validators,

        'format': ['p_ignore_missing', 'clean_format', 'unicode_safe'],
        'created': ['p_ignore_missing'],
        'position': ['p_not_empty'],
        'last_modified': [],
        'cache_last_updated': [],
        'package_id': [],
        'size': [],
        'state': [],
        'mimetype': [],
        'cache_url': [],
        'name': [],
        'description': [],
        'mimetype_inner': [],
        'resource_type': [],
        'url_type': [],
    }
