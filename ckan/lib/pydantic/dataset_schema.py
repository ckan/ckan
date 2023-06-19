import pydantic
from typing import Any, Dict, List, Optional

from ckan.lib.pydantic.base import CKANBaseModel
from ckan.lib.pydantic.resource_schema import DefaultResourceSchema, DefaultResourceUpdateSchema
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
    resources: Optional[List[DefaultResourceSchema]]
    tags: Optional[List[DefaultTagSchema]]
    tag_string: Optional[str]
    plugin_data: Optional[Dict[str, Any]]
    extras: Optional[List[DefaultExtrasSchema]]
    save: Optional[str]
    _return_to: Optional[str]
    relationships_as_object: Optional[List[DefaultRelationshipSchema]]
    relationships_as_subject: Optional[List[DefaultRelationshipSchema]]
    groups: Optional[Dict[str, Any]]

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
        # 'groups': {
        #     'id': ["ignore_missing", "unicode_safe"],
        #     'name': ["ignore_missing", "unicode_safe"],
        #     'title': ["ignore_missing", "unicode_safe"],
        #     '__extras': ["ignore"],
        # }
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
    id: str
    tags: List[DefaultTagSchema]
    resources: List[DefaultResourceSchema]
    state: Optional[str]
    isopen: Optional[str]
    license_url: Optional[str]
    tracking_summary: Optional[str]
