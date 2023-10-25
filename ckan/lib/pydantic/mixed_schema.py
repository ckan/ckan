from typing import  Optional, Dict, Any
from ckan.lib.pydantic.base import CKANBaseModel


class DefaultExtrasSchema(CKANBaseModel):

    id: Optional[str]
    key: Optional[str]
    value: Optional[str]
    state: Optional[str]
    deleted: Optional[str]
    revision_timestamp: Optional[str]
    _extras: Optional[Dict[str, Any]]

    _validators = {
       'id': ['p_ignore'],
        'key': ['p_not_empty', 'p_extra_key_not_in_root_schema', 'unicode_safe'],
        'value': ['p_not_missing'],
        'state': ['p_ignore'],
        'deleted': ['p_ignore_missing'],
        'revision_timestamp': ['p_ignore'],
        '_extras': ['p_ignore'],
    }


class DefaultRelationshipSchema(CKANBaseModel):

    id: Optional[str]
    subject: Optional[str]
    object: Optional[str]
    type: str
    comment: Optional[str]
    state: Optional[str]

    _validators = {
        'id': ['p_ignore_missing', 'unicode_safe'],
        'subject': ['Pignore_missing', 'unicode_safe'],
        'object': ['p_ignore_missing', 'unicode_safe'],
        'type': ['p_not_empty',
                 'one_of(ckan.model.PackageRelationship.get_all_types())'],
        'comment': ['p_ignore_missing', 'unicode_safe'],
        'state': ['p_ignore'],
    }


class DefaultCreateRelationshipSchema(DefaultRelationshipSchema):

    _validators = {
        **DefaultRelationshipSchema._validators,

        'id': ['p_empty'],
        'subject': ['p_not_empty', 'unicode_safe', 'package_id_or_name_exists'],
        'object': ['p_not_empty', 'unicode_safe', 'package_id_or_name_exists']
    }


class DefaultUpdateRelationshipSchema(DefaultRelationshipSchema):

    _validators = {
        **DefaultRelationshipSchema._validators,

        'id': ['p_ignore_missing', 'package_id_not_changed'],

        'subject': ['p_ignore_missing'],
        'object': ['p_ignore_missing'],
        'type': ['p_ignore_missing']
    }
