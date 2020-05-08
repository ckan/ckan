# encoding: utf-8

from six import text_type

import ckan.plugins as p
import ckanext.datastore.logic.schema as dsschema

get_validator = p.toolkit.get_validator

not_missing = get_validator('not_missing')
not_empty = get_validator('not_empty')
ignore_missing = get_validator('ignore_missing')
empty = get_validator('empty')
boolean_validator = get_validator('boolean_validator')


def datapusher_submit_schema():
    schema = {
        'resource_id': [not_missing, not_empty, text_type],
        'id': [ignore_missing],
        'set_url_type': [ignore_missing, boolean_validator],
        'ignore_hash': [ignore_missing, boolean_validator],
        '__junk': [empty],
        '__before': [dsschema.rename('id', 'resource_id')]
    }
    return schema
