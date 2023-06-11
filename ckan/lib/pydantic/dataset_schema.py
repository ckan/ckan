import pydantic
from typing import Any, Dict, List, Optional

from ckan.lib.pydantic.base import CKANBaseModel
from ckan.lib.pydantic.resource_schema import DefaultResourceSchema
from ckan.lib.pydantic.tag_schema import DefaultTagSchema
from ckan.lib.pydantic.mixed_schema import DefaultExtrasSchema
from ckan.lib.pydantic.mixed_schema import DefaultRelationshipSchema


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
    private: Optional[str]
    resources: Optional[List[DefaultResourceSchema]] = []
    tags: Optional[List[DefaultTagSchema]]
    tag_string: Optional[str]
    plugin_data: Optional[Dict[str, Any]]
    extras: Optional[List[DefaultExtrasSchema]]
    _save: Optional[str]
    _return_to: Optional[str]
    relationships_as_object: Optional[List[DefaultRelationshipSchema]]
    relationships_as_subject: Optional[List[DefaultRelationshipSchema]]
    groups: Optional[Dict[str, Any]]

    _validators = {
        'id': [
            "pydantic_empty_if_not_sysadmin", "pydantic_ignore_missing", 
            "unicode_safe", "package_id_does_not_exist"
        ],
        'name': [
            "pydantic_not_empty", "unicode_safe", "name_validator", 
            "pydantic_package_name_validator"
        ],
        'title': []
    }

    @pydantic.root_validator(pre=False)
    def convert_to_extras(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        '''
        Convert given field into an extra field.
        '''

        all_required_field_names = (
            {
            field.alias for field in cls.__fields__.values() 
            if field.alias != 'extras'
            }
        )

        extras = list()
        if not 'extras' in values:
            values['extras'] = list()

        for field_name, field_value in values.items():
            if (
                field_name not in ["_ckan_phase", "save", "pkg_name", "extras", "errors"]
                and field_name not in all_required_field_names
            ):
                extras.append({'key': field_name, 'value': field_value})
        values['extras'] = extras
        return values


class DefaultUpdatePackageSchema(DefaultCreatePackageSchema):

    resources: List[DefaultResourceSchema]

    # Users can (optionally) supply the package id when updating a package, but
    # only to identify the package to be updated, they cannot change the id.
    id: Optional[str]

    # Supplying the package name when updating a package is optional (you can
    # supply the id to identify the package instead).
    name: str

    # Supplying the package title when updating a package is optional, if it's
    # not supplied the title will not be changed.
    title: str

    owner_org: Optional[str]


class DefaultShowPackageSchema(DefaultCreatePackageSchema):
    id: str
    tags: List[DefaultTagSchema]
    resources: List[DefaultResourceSchema]
    state: Optional[str]
    isopen: Optional[str]
    license_url: Optional[str]
    tracking_summary: Optional[str]
