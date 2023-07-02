from typing import Optional, List, Any, Dict
from typing_extensions import Literal

from .base import CKANBaseModel
from .mixed_schema import DefaultExtrasSchema

class Packages(CKANBaseModel):
    id: str
    title: Optional[str]
    name: Optional[str]
    _extras: Optional[Dict[str, Any]]

    _validators = {
        "id": ['p_not_empty', 'unicode_safe', 'package_id_or_name_exists'],
        "title": ['p_ignore_missing', 'unicode_safe'],
        "name": ['p_ignore_missing', 'unicode_safe'],
        "_extras": ['p_ignore']
    }


class Users(CKANBaseModel):
    name: str
    capacity: Optional[str]
    _extras: Optional[Dict[str, Any]]

    _validators = {
        "name": ['p_not_empty', 'unicode_safe'],
        "capacity": ['p_ignore_missing'],
        "_extras": ['p_ignore']
    }


class Groups(CKANBaseModel):
    name: str
    capacity: Optional[str]
    _extras: Optional[Dict[str, Any]]

    _validators = {
        "name": ['p_not_empty', 'unicode_safe'],
        "capacity": ['p_ignore_missing'],
        "_extras": ['p_ignore']
    }


class DefaultGroupSchema(CKANBaseModel):

    id: Optional[str]
    name: str
    title: Optional[str]
    description: Optional[str]
    image_url:  Optional[str]
    image_display_url: Optional[str]
    type: Optional[str]
    state: Optional[str]
    created: Optional[str]
    is_organization: Optional[bool]
    approval_status: Optional[str]
    extras: Optional[List[DefaultExtrasSchema]]
    _extras: Literal[None]
    _junk: Literal[None]
    packages: Optional[List[Packages]]
    users: Optional[List[Users]]
    groups: Optional[List[Groups]]

    _validators = {
        'id': ['p_ignore_missing', 'unicode_safe'],
        'name': ['p_not_empty', 'unicode_safe', 'name_validator', 
                 'p_group_name_validator'],
        'title': ['p_ignore_missing', 'unicode_safe'],
        'description': ['p_ignore_missing', 'unicode_safe'],
        'image_url': ['p_ignore_missing', 'unicode_safe'],
        'image_display_url': ['p_ignore_missing', 'unicode_safe'],
        'type': ['p_ignore_missing', 'unicode_safe'],
        'state': ['p_ignore_not_group_admin', 'p_ignore_missing'],
        'created': ['p_ignore'],
        'is_organization': ['p_ignore_missing'],
        'approval_status': ['p_ignore_missing', 'unicode_safe'],
        'extras': [DefaultExtrasSchema],
        '_extras': ['p_ignore'],
        '_junk': ['p_ignore'],
        'packages': [Packages],
        'users': [Users],
        'groups': [Groups]
    }


class GroupFormSchema(DefaultGroupSchema):
    _validators = {
        **DefaultGroupSchema._validators,

        'packages': [Packages._validators.update({
            "name": ['p_not_empty', 'unicode_safe'],
            "title": ['p_ignore_missing'],
            "__extras": ['p_ignore']
        }), Packages],

        'users': [Users._validators.update({
            "name": ['p_not_empty', 'unicode_safe'],
            "capacity": ['p_ignore_missing'],
            "__extras": ['p_ignore']
        })]
    }


class DefaultUpdateGroupSchema(DefaultGroupSchema):
    name: Optional[str]  # type: ignore

    _validators = {
        **DefaultGroupSchema._validators,
        'name': ['p_ignore_missing', 'p_group_name_validator', 'unicode_safe']
    }


class DefaultShowGroupSchema(DefaultGroupSchema):

    num_followers: Optional[str]
    display_name: Optional[str]
    package_count: Optional[str]
    member_count: Optional[str]

    _validators = {
        **DefaultGroupSchema._validators,

        'num_followers': [],
        'created': [],
        'display_name': [],

        'extras': [DefaultExtrasSchema._validators.update({
            '_extras': ['p_keep_extras']
        }), DefaultExtrasSchema],

        'package_count': ['p_ignore_missing'],
        'member_count': ['p_ignore_missing'],

        'packages': [Packages._validators.update({
            '_extras': ['p_keep_extras']
        }), Packages],

        'state': [],

        'users': [Users._validators.update({
            '_extras': ['p_keep_extras']
        }), Users]
    }
