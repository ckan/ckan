from ckan.lib.navl.validators import (ignore_missing,
                                      keep_extras,
                                      not_empty,
                                      empty,
                                      ignore,
                                      both_not_empty,
                                      if_empty_same_as,
                                      not_missing
                                     )
from ckan.logic.validators import (package_id_not_changed,
                                             package_id_exists,
                                             package_id_or_name_exists,
                                             extras_unicode_convert,
                                             name_validator,
                                             package_name_validator,
                                             group_name_validator,
                                             tag_length_validator,
                                             tag_name_validator,
                                             tag_not_uppercase)
from formencode.validators import OneOf
import ckan.model

    
def default_resource_schema():

    schema = {
        'id': [ignore_missing, unicode],
        'revistion_id': [ignore_missing, unicode],
        'resource_group_id': [ignore],
        'package_id': [ignore],
        'url': [not_empty, unicode],#, URL(add_http=False)],
        'description': [ignore_missing, unicode],
        'format': [ignore_missing, unicode],
        'hash': [ignore_missing, unicode],
        'state': [ignore],
        'position': [ignore],
        '__extras': [ignore_missing, extras_unicode_convert, keep_extras],
    }

    return schema

def default_tags_schema():

    schema = {
        'name': [not_empty,
                 unicode,
                 tag_length_validator,
                 tag_name_validator,
                 tag_not_uppercase],
    }
    return schema

def default_package_schema():

    schema = {
        'id': [ignore_missing, unicode, package_id_exists],
        'revision_id': [ignore_missing, unicode],
        'name': [not_empty, unicode, name_validator, package_name_validator],
        'title': [if_empty_same_as("name"), unicode],
        'author': [ignore_missing, unicode],
        'author_email': [ignore_missing, unicode],
        'maintainer': [ignore_missing, unicode],
        'maintainer_email': [ignore_missing, unicode],
        'license_id': [ignore_missing, unicode],
        'notes': [ignore_missing, unicode],
        'url': [ignore_missing, unicode],#, URL(add_http=False)],
        'version': [ignore_missing, unicode],
        'state': [ignore],
        '__extras': [ignore],
        '__junk': [empty],
        'resources': default_resource_schema(),
        'tags': default_tags_schema(),
        'extras': default_extras_schema(),
        'relationships_as_object': default_relationship_schema(),
        'relationships_as_subject': default_relationship_schema(),
        'groups': {
            '__extras': [ignore],
        }
    }

    return schema

def default_create_package_schema():

    schema = default_package_schema()
    schema["id"] = [empty]

    return schema

def default_update_package_schema():

    schema = default_package_schema()
    schema["id"] = [ignore_missing, package_id_not_changed]
    schema["name"] = [ignore_missing, name_validator, package_name_validator, unicode]
    schema["title"] = [ignore_missing, unicode]

    return schema


def default_group_schema():

    schema = {
        'id': [ignore_missing, unicode],
        'revision_id': [ignore_missing, unicode],
        'name': [not_empty, unicode, name_validator, group_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'state': [ignore],
        'created': [ignore],
        'extras': default_extras_schema(),
        'packages': {
            "id": [not_empty, unicode, package_id_or_name_exists],
            "__extras": [ignore]
        }
    }
    return schema

def default_update_group_schema():
    schema = default_group_schema()
    schema["name"] = [ignore_missing, group_name_validator, unicode]
    return schema

def default_extras_schema():

    schema = {
        'id': [ignore],
        'key': [not_empty, unicode],
        'value': [not_missing, unicode],
        'state': [ignore],
    }
    return schema

def default_relationship_schema():

     schema = {
         'id': [ignore_missing, unicode],
         'subject_package_id': [ignore_missing, unicode],
         'object_package_id': [ignore_missing, unicode],
         'type': [not_empty, OneOf(ckan.model.PackageRelationship.get_all_types())],
         'comment': [ignore_missing, unicode],
         'state': [ignore],
     }


