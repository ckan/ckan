import pydantic
from typing import Any, Dict, List, Optional

from ckan.lib.pydantic.resource_schema import (
    DefaultResourceSchema, 
    DefaultResourceUpdateSchema, 
    DefaultResourceForPackageShow
)

from ckan.lib.pydantic.base import CKANBaseModel
from ckan.lib.pydantic.tag_schema import DefaultTagSchema
from ckan.lib.pydantic.mixed_schema import DefaultExtrasSchema
from ckan.lib.pydantic.mixed_schema import DefaultRelationshipSchema


class Groups(CKANBaseModel):
    id: Optional[str]
    name: Optional[str]
    title: Optional[str]

    _validators = {
        'id': ["p_ignore_missing", "unicode_safe"],
        'name': ["p_ignore_missing", "unicode_safe"],
        'title': ["p_ignore_missing", "unicode_safe"],
        '__extras': ["p_ignore"],
    }


class DefaultCreatePackageSchema(CKANBaseModel):
    id: Optional[str] 
    name: str
    title: str
    author: Optional[str]
    author_email: Optional[str]
    maintainer: Optional[str]
    maintainer_email: Optional[str]
    license_id: Optional[str]
    notes: Optional[str]
    url: Optional[str]
    version: Optional[str]
    state: Optional[str]
    type: Optional[str]
    owner_org: Optional[str]
    private: Optional[bool]
    resources: Optional[List[DefaultResourceSchema]]
    tags: Optional[List[DefaultTagSchema]]
    tag_string: Optional[str]
    plugin_data: Optional[Dict[str, Any]]
    extras: Optional[List[DefaultExtrasSchema]]
    save: Optional[str]
    return_to: Optional[str]
    relationships_as_object: Optional[List[DefaultRelationshipSchema]]
    relationships_as_subject: Optional[List[DefaultRelationshipSchema]]
    groups: Optional[List[Groups]]

    _validators = {
        'id': ["p_empty_if_not_sysadmin", "p_ignore_missing",  
               "unicode_safe", "package_id_does_not_exist"],
        'name': ["p_not_empty", "unicode_safe", "name_validator", 
                 "p_package_name_validator"],
        'title': ["p_if_empty_same_as(name)", "unicode_safe"],
        'author': ["p_ignore_missing", "unicode_safe"],
        'author_email': ["p_ignore_missing", "unicode_safe", 
                         "strip_value", "email_validator"],
        'maintainer': ["p_ignore_missing", "unicode_safe"],
        'maintainer_email': ["p_ignore_missing", "unicode_safe", 
                             "strip_value", "email_validator"],
        'license_id': ["p_ignore_missing", "unicode_safe"],
        'notes': ["p_ignore_missing", "unicode_safe"],
        'url': ["p_ignore_missing", "unicode_safe"],
        'version': ["p_ignore_missing", "unicode_safe", 
                    "package_version_validator"],
        'state': ["p_ignore_not_package_admin", "p_ignore_missing"],
        'type': ["p_ignore_missing", "unicode_safe"],
        'owner_org': ["p_owner_org_validator", "unicode_safe"],
        'private': ["p_ignore_missing", "boolean_validator",
                    "p_datasets_with_no_organization_cannot_be_private"],
        '__extras': ["p_ignore"],
        'resources': [DefaultResourceSchema],
        'tags': [DefaultTagSchema],
        'tag_string': ["p_ignore_missing", "tag_string_convert"],
        'plugin_data': ["p_ignore_missing", "json_object", "ignore_not_sysadmin"],
        'extras': [DefaultExtrasSchema],
        'save': ["p_ignore"],
        'return_to': ["p_ignore"],
        'relationships_as_object': [DefaultRelationshipSchema],
        'relationships_as_subject': [DefaultRelationshipSchema],
        'groups': [Groups]
    }


class DefaultUpdatePackageSchema(DefaultCreatePackageSchema):

    resources: Optional[List[DefaultResourceUpdateSchema]]  # type: ignore

    _validators = {
        **DefaultCreatePackageSchema._validators,

        'resources': [DefaultResourceUpdateSchema],
        # # Users can (optionally) supply the package id when updating a package, but
        # # only to identify the package to be updated, they cannot change the id.
        'id': ["p_ignore_missing", "package_id_not_changed"],
        # Supplying the package name when updating a package is optional (you can
        # supply the id to identify the package instead).
        "name": [
            "p_ignore_missing", "name_validator", "p_package_name_validator",
            "unicode_safe"
        ],
        # Supplying the package title when updating a package is optional, if it's
        # not supplied the title will not be changed.
        "title": ["p_ignore_missing", "unicode_safe"],
        "owner_org": ["p_ignore_missing", "p_owner_org_validator", "unicode_safe"]
    }


class DefaultShowPackageSchema(DefaultCreatePackageSchema):

    organization: Optional[Dict[str, Any]]
    resources: Optional[List[DefaultResourceForPackageShow]] # type: ignore
    metadata_created: str
    metadata_modified: str
    creator_user_id: str
    num_resources: int
    num_tags: int
    owner_org: Optional[str]
    tracking_summary: Optional[Dict[str, Any]]
    license_title: Optional[str]
    isopen: Optional[bool]
    license_url: Optional[str]

    _validators = {
        **DefaultCreatePackageSchema._validators,

        'id': [],
        # 'tags': {'__extras': ['p_keep_extras']},
        'name': ["p_not_empty", "unicode_safe", "name_validator"],

        'resources': [DefaultResourceForPackageShow],

        'state': ['p_ignore_missing'],
        'isopen': ['p_ignore_missing'],
        'license_url': ['p_ignore_missing'],

        # 'groups': {
        #     'description': ['p_ignore_missing'],
        #     'display_name': ['p_ignore_missing'],
        #     'image_display_url': ['p_ignore_missing'],
        # },

        # Remove validators for several keys from the schema so validation doesn't
        # strip the keys from the package dicts if the values are 'missing' (i.e.
        # None).
        'author': [],
        'author_email': [],
        'maintainer': [],
        'maintainer_email': [],
        'license_id': [],
        'notes': [],
        'url': [],
        'version': [],

        # Add several keys that are missing from default_create_package_schema(),
        # so validation doesn't strip the keys from the package dicts.
        'metadata_created': [],
        'metadata_modified': [],
        'creator_user_id': [],
        'num_resources': [],
        'num_tags': [],
        'organization': [],
        'owner_org': [],
        'private': [],
        'tracking_summary': ['p_ignore_missing'],
        'license_title': []
    }


class DefaultSearchPackageSchema(CKANBaseModel):

    q: Optional[str]
    fl: Optional[str]
    fq: Optional[str]
    rows: Optional[int]
    sort: Optional[str]
    start: Optional[int]
    qf: Optional[str]
    facet: Optional[str]
    facet_mincount: Optional[int] = pydantic.Field(None, alias='facet.mincount')
    facet_limit: Optional[int] = pydantic.Field(None, alias='facet.limit')
    facet_field: Optional[List[str]] = pydantic.Field(None, alias='facet.field')
    extras: Optional[DefaultExtrasSchema]

    _validators = {
        'q': ['p_ignore_missing', 'unicode_safe'],
        'fl': ['p_ignore_missing', 'convert_to_list_if_string'],
        'fq': ['p_ignore_missing', 'unicode_safe'],
        'rows': ['p_default(10)', 'natural_number_validator'], # 'limit_to_configured_maximum(ckan.search.rows_max)'
        'sort': ['p_ignore_missing', 'unicode_safe'],
        'start': ['p_ignore_missing', 'natural_number_validator'],
        'qf': ['p_ignore_missing', 'unicode_safe'],
        'facet': ['p_ignore_missing', 'unicode_safe'],
        'facet.mincount': ['p_ignore_missing', 'natural_number_validator'],
        'facet.limit': ['p_ignore_missing', 'int_validator'],
        'facet.field': ['p_ignore_missing', 'convert_to_json_if_string',
                        'p_list_of_strings'],
        'extras': ['p_ignore_missing', DefaultExtrasSchema]
    }
