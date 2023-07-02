import pydantic
from typing import Optional, Dict, Any
from ckan.lib.pydantic.base import CKANBaseModel


class UserCreateSchema(CKANBaseModel):
    id: Optional[str]
    name: str
    fullname: Optional[str]
    password: str = pydantic.Field(..., min_length=8)
    password_hash: Optional[str]
    email: str
    about: Optional[str]
    created: Optional[str]
    sysadmin: Optional[bool]
    reset_key: Optional[str]
    activity_streams_email_notifications: Optional[str]
    state: Optional[str]
    image_url: Optional[str]
    image_display_url: Optional[str]
    plugin_extras: Optional[Dict[str, Any]]

    _validators = {
        'id': ['p_ignore_missing', 'unicode_safe'],
        'name': ['p_not_empty', 'name_validator', 'p_user_name_validator', 
                 'unicode_safe'],
        'fullname': ['p_ignore_missing', 'unicode_safe'],
        'password': ['p_user_password_not_empty', 'p_ignore_missing', 
                     'unicode_safe'],
        'password_hash': ['p_ignore_missing', 'p_ignore_not_sysadmin', 'unicode_safe'],
        'email': ['p_not_empty', 'email_validator', 'unicode_safe'],
        'about': ['ignore_missing', 'user_about_validator', 'unicode_safe'],
        'created': ['p_ignore'],
        'sysadmin': ['p_ignore_missing', 'p_ignore_not_sysadmin'],
        'reset_key': ['p_ignore'],
        'activity_streams_email_notifications': ['p_ignore_missing',
                                                 'boolean_validator'],
        'state': ['p_ignore_missing', 'p_ignore_not_sysadmin'],
        'image_url': ['p_ignore_missing', 'unicode_safe'],
        'image_display_url': ['p_ignore_missing', 'unicode_safe'],
        'plugin_extras': ['p_ignore_missing', 'json_object', 'p_ignore_not_sysadmin'],
    }
