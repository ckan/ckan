
from typing import Optional
from ckan.lib.pydantic.base import CKANBaseModel


class DefaultTagSchema(CKANBaseModel):

    name: str
    vocabulary_id: Optional[str]
    revision_timestamp: Optional[str]
    state: Optional[str]
    display_name: Optional[str]

    _validators = {
        'name': ['p_not_missing',
                 'p_not_empty',
                 'unicode_safe',
                 'tag_length_validator',
                 'tag_name_validator',
                 ],
        'vocabulary_id': ['p_ignore_missing',
                          'unicode_safe',
                          'vocabulary_id_exists'],
        'revision_timestamp': ['p_ignore'],
        'state': ['p_ignore'],
        'display_name': ['p_ignore'],
        
    }


class DefaultCreateTagSchema(DefaultTagSchema):

    _validators = {
        **DefaultTagSchema._validators,

        # When creating a tag via the tag_create() logic action function, a
        # vocabulary_id _must_ be given (you cannot create free tags via this
        # function).
        'vocabulary_id': ['p_not_missing', 'p_not_empty', 'unicode_safe',
                          'vocabulary_id_exists', 'tag_not_in_vocabulary'],
        # You're not allowed to specify your own ID when creating a tag.
        'id': ['p_empty']
    }
