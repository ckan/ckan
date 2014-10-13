from ckan.lib.navl.validators import (ignore_missing,
                                      keep_extras,
                                      not_empty,
                                      empty,
                                      ignore,
                                      if_empty_same_as,
                                      not_missing,
                                      ignore_empty
                                     )
from ckan.logic.validators import (package_id_not_changed,
                                   package_id_exists,
                                   package_id_or_name_exists,
                                   extras_unicode_convert,
                                   name_validator,
                                   package_name_validator,
                                   package_version_validator,
                                   group_name_validator,
                                   tag_length_validator,
                                   tag_name_validator,
                                   tag_string_convert,
                                   duplicate_extras_key,
                                   ignore_not_package_admin,
                                   ignore_not_group_admin,
                                   ignore_not_sysadmin,
                                   no_http,
                                   tag_not_uppercase,
                                   user_name_validator,
                                   user_password_validator,
                                   user_both_passwords_entered,
                                   user_passwords_match,
                                   user_password_not_empty,
                                   isodate,
                                   int_validator,
                                   natural_number_validator,
                                   is_positive_integer,
                                   boolean_validator,
                                   user_about_validator,
                                   vocabulary_name_validator,
                                   vocabulary_id_not_changed,
                                   vocabulary_id_exists,
                                   user_id_exists,
                                   user_id_or_name_exists,
                                   object_id_validator,
                                   activity_type_exists,
                                   resource_id_exists,
                                   tag_not_in_vocabulary,
                                   group_id_exists,
                                   owner_org_validator,
                                   user_name_exists,
                                   role_exists,
                                   url_validator,
                                   datasets_with_no_organization_cannot_be_private,
                                   list_of_strings,
                                   no_loops_in_hierarchy,
                                   )
from ckan.logic.converters import (convert_user_name_or_id_to_id,
                                   convert_package_name_or_id_to_id,
                                   convert_group_name_or_id_to_id,
                                   convert_to_json_if_string,
                                   remove_whitespace,
                                   )
from formencode.validators import OneOf
import ckan.model
import ckan.lib.maintain as maintain

def default_resource_schema():

    schema = {
        'id': [ignore_empty, unicode],
        'revision_id': [ignore_missing, unicode],
        'resource_group_id': [ignore],
        'package_id': [ignore],
        'url': [not_empty, unicode, remove_whitespace],
        'description': [ignore_missing, unicode],
        'format': [ignore_missing, unicode],
        'hash': [ignore_missing, unicode],
        'state': [ignore],
        'position': [ignore],
        'revision_timestamp': [ignore],
        'name': [ignore_missing, unicode],
        'resource_type': [ignore_missing, unicode],
        'url_type': [ignore_missing, unicode],
        'mimetype': [ignore_missing, unicode],
        'mimetype_inner': [ignore_missing, unicode],
        'webstore_url': [ignore_missing, unicode],
        'cache_url': [ignore_missing, unicode],
        'size': [ignore_missing, int_validator],
        'created': [ignore_missing, isodate],
        'last_modified': [ignore_missing, isodate],
        'cache_last_updated': [ignore_missing, isodate],
        'webstore_last_updated': [ignore_missing, isodate],
        'tracking_summary': [ignore_missing],
        'datastore_active': [ignore],
        '__extras': [ignore_missing, extras_unicode_convert, keep_extras],
    }

    return schema

def default_update_resource_schema():
    schema = default_resource_schema()
    return schema

def default_tags_schema():
    schema = {
        'name': [not_missing,
                 not_empty,
                 unicode,
                 tag_length_validator,
                 tag_name_validator,
                ],
        'vocabulary_id': [ignore_missing, unicode, vocabulary_id_exists],
        'revision_timestamp': [ignore],
        'state': [ignore],
        'display_name': [ignore],
    }
    return schema

def default_create_tag_schema():
    schema = default_tags_schema()
    # When creating a tag via the tag_create() logic action function, a
    # vocabulary_id _must_ be given (you cannot create free tags via this
    # function).
    schema['vocabulary_id'] = [not_missing, not_empty, unicode,
            vocabulary_id_exists, tag_not_in_vocabulary]
    # You're not allowed to specify your own ID when creating a tag.
    schema['id'] = [empty]
    return schema


def default_create_package_schema():
    schema = {
        '__before': [duplicate_extras_key, ignore],
        'id': [empty],
        'revision_id': [ignore],
        'name': [not_empty, unicode, name_validator, package_name_validator],
        'title': [if_empty_same_as("name"), unicode],
        'author': [ignore_missing, unicode],
        'author_email': [ignore_missing, unicode],
        'maintainer': [ignore_missing, unicode],
        'maintainer_email': [ignore_missing, unicode],
        'license_id': [ignore_missing, unicode],
        'notes': [ignore_missing, unicode],
        'url': [ignore_missing, unicode],#, URL(add_http=False)],
        'version': [ignore_missing, unicode, package_version_validator],
        'state': [ignore_not_package_admin, ignore_missing],
        'type': [ignore_missing, unicode],
        'owner_org': [owner_org_validator, unicode],
        'log_message': [ignore_missing, unicode, no_http],
        'private': [ignore_missing, boolean_validator,
            datasets_with_no_organization_cannot_be_private],
        '__extras': [ignore],
        '__junk': [empty],
        'resources': default_resource_schema(),
        'tags': default_tags_schema(),
        'tag_string': [ignore_missing, tag_string_convert],
        'extras': default_extras_schema(),
        'save': [ignore],
        'return_to': [ignore],
        'relationships_as_object': default_relationship_schema(),
        'relationships_as_subject': default_relationship_schema(),
        'groups': {
            'id': [ignore_missing, unicode],
            'name': [ignore_missing, unicode],
            'title': [ignore_missing, unicode],
            '__extras': [ignore],
        }
    }
    return schema

def default_update_package_schema():
    schema = default_create_package_schema()

    # Users can (optionally) supply the package id when updating a package, but
    # only to identify the package to be updated, they cannot change the id.
    schema['id'] = [ignore_missing, package_id_not_changed]

    # Supplying the package name when updating a package is optional (you can
    # supply the id to identify the package instead).
    schema['name'] = [ignore_missing, name_validator, package_name_validator,
            unicode]

    # Supplying the package title when updating a package is optional, if it's
    # not supplied the title will not be changed.
    schema['title'] = [ignore_missing, unicode]

    schema['owner_org'] = [ignore_missing, owner_org_validator, unicode]

    return schema

def default_show_package_schema():
    schema = default_create_package_schema()

    # Don't strip ids from package dicts when validating them.
    schema['id'] = []

    schema.update({
        'tags': {'__extras': [ckan.lib.navl.validators.keep_extras]}})

    # Add several keys to the 'resources' subschema so they don't get stripped
    # from the resource dicts by validation.
    schema['resources'].update({
        'created': [ckan.lib.navl.validators.ignore_missing],
        'position': [not_empty],
        'last_modified': [ckan.lib.navl.validators.ignore_missing],
        'cache_last_updated': [ckan.lib.navl.validators.ignore_missing],
        'webstore_last_updated': [ckan.lib.navl.validators.ignore_missing],
        'revision_timestamp': [],
        'resource_group_id': [],
        'cache_last_updated': [],
        'webstore_last_updated': [],
        'size': [],
        'state': [],
        'last_modified': [],
        'mimetype': [],
        'cache_url': [],
        'name': [],
        'webstore_url': [],
        'mimetype_inner': [],
        'resource_type': [],
        'url_type': [],
    })

    schema.update({
        'state': [ckan.lib.navl.validators.ignore_missing],
        'isopen': [ignore_missing],
        'license_url': [ignore_missing],
        })

    schema['groups'].update({
        'description': [ignore_missing],
        'display_name': [ignore_missing],
        'image_display_url': [ignore_missing],
        })

    # Remove validators for several keys from the schema so validation doesn't
    # strip the keys from the package dicts if the values are 'missing' (i.e.
    # None).
    schema['author'] = []
    schema['author_email'] = []
    schema['maintainer'] = []
    schema['maintainer_email'] = []
    schema['license_id'] = []
    schema['notes'] = []
    schema['url'] = []
    schema['version'] = []

    # Add several keys that are missing from default_create_package_schema(), so
    # validation doesn't strip the keys from the package dicts.
    schema['metadata_created'] = []
    schema['metadata_modified'] = []
    schema['creator_user_id'] = []
    schema['num_resources'] = []
    schema['num_tags'] = []
    schema['organization'] = []
    schema['owner_org'] = []
    schema['private'] = []
    schema['revision_id'] = []
    schema['revision_timestamp'] = []
    schema['tracking_summary'] = []
    schema['license_title'] = []

    return schema

def default_group_schema():

    schema = {
        'id': [ignore_missing, unicode],
        'revision_id': [ignore],
        'name': [not_empty, unicode, name_validator, group_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'image_url': [ignore_missing, unicode],
        'image_display_url': [ignore_missing, unicode],
        'type': [ignore_missing, unicode],
        'state': [ignore_not_group_admin, ignore_missing],
        'created': [ignore],
        'is_organization': [ignore_missing],
        'approval_status': [ignore_missing, unicode],
        'extras': default_extras_schema(),
        '__extras': [ignore],
        '__junk': [ignore],
        'packages': {
            "id": [not_empty, unicode, package_id_or_name_exists],
            "title":[ignore_missing, unicode],
            "name":[ignore_missing, unicode],
            "__extras": [ignore]
        },
        'users': {
            "name": [not_empty, unicode],
            "capacity": [ignore_missing],
            "__extras": [ignore]
        },
        'groups': {
            "name": [not_empty, no_loops_in_hierarchy, unicode],
            "capacity": [ignore_missing],
            "__extras": [ignore]
        }
    }
    return schema

def group_form_schema():
    schema = default_group_schema()
    #schema['extras_validation'] = [duplicate_extras_key, ignore]
    schema['packages'] = {
        "name": [not_empty, unicode],
        "title": [ignore_missing],
        "__extras": [ignore]
    }
    schema['users'] = {
        "name": [not_empty, unicode],
        "capacity": [ignore_missing],
        "__extras": [ignore]
    }
    schema['display_name'] = [ignore_missing]
    return schema


def default_update_group_schema():
    schema = default_group_schema()
    schema["name"] = [ignore_missing, group_name_validator, unicode]
    return schema


def default_related_schema():
    schema = {
        'id': [ignore_missing, unicode],
        'title': [not_empty, unicode],
        'description': [ignore_missing, unicode],
        'type': [not_empty, unicode],
        'image_url': [ignore_missing, unicode, url_validator],
        'url': [ignore_missing, unicode, url_validator],
        'owner_id': [not_empty, unicode],
        'created': [ignore],
        'featured': [ignore_missing, int],
    }
    return schema


def default_update_related_schema():
    schema = default_related_schema()
    schema['id'] = [not_empty, unicode]
    schema['title'] = [ignore_missing, unicode]
    schema['type'] = [ignore_missing, unicode]
    schema['owner_id'] = [ignore_missing, unicode]
    return schema


def default_extras_schema():

    schema = {
        'id': [ignore],
        'key': [not_empty, unicode],
        'value': [not_missing],
        'state': [ignore],
        'deleted': [ignore_missing],
        'revision_timestamp': [ignore],
        '__extras': [ignore],
    }
    return schema

def default_relationship_schema():

    schema = {
         'id': [ignore_missing, unicode],
         'subject': [ignore_missing, unicode],
         'object': [ignore_missing, unicode],
         'type': [not_empty, OneOf(ckan.model.PackageRelationship.get_all_types())],
         'comment': [ignore_missing, unicode],
         'state': [ignore],
    }
    return schema

def default_create_relationship_schema():

    schema = default_relationship_schema()
    schema['id'] = [empty]
    schema['subject'] = [not_empty, unicode, package_id_or_name_exists]
    schema['object'] = [not_empty, unicode, package_id_or_name_exists]

    return schema

def default_update_relationship_schema():

    schema = default_relationship_schema()
    schema['id'] = [ignore_missing, package_id_not_changed]

    # Todo: would like to check subject, object & type haven't changed, but
    # no way to do this in schema
    schema['subject'] = [ignore_missing]
    schema['object'] = [ignore_missing]
    schema['type'] = [ignore_missing]

    return schema




def default_user_schema():

    schema = {
        'id': [ignore_missing, unicode],
        'name': [not_empty, name_validator, user_name_validator, unicode],
        'fullname': [ignore_missing, unicode],
        'password': [user_password_validator, user_password_not_empty, ignore_missing, unicode],
        'email': [not_empty, unicode],
        'about': [ignore_missing, user_about_validator, unicode],
        'created': [ignore],
        'openid': [ignore_missing],
        'sysadmin': [ignore_missing, ignore_not_sysadmin],
        'apikey': [ignore],
        'reset_key': [ignore],
        'activity_streams_email_notifications': [ignore_missing],
        'state': [ignore_missing],
    }
    return schema

def user_new_form_schema():
    schema = default_user_schema()

    schema['password1'] = [unicode,user_both_passwords_entered,user_password_validator,user_passwords_match]
    schema['password2'] = [unicode]

    return schema

def user_edit_form_schema():
    schema = default_user_schema()

    schema['password'] = [ignore_missing]
    schema['password1'] = [ignore_missing,unicode,user_password_validator,user_passwords_match]
    schema['password2'] = [ignore_missing,unicode]

    return schema

def default_update_user_schema():
    schema = default_user_schema()

    schema['name'] = [ignore_missing, name_validator, user_name_validator, unicode]
    schema['password'] = [user_password_validator,ignore_missing, unicode]

    return schema

def default_user_invite_schema():
    schema = {
        'email': [not_empty, unicode],
        'group_id': [not_empty],
        'role': [not_empty],
    }
    return schema

def default_task_status_schema():
    schema = {
        'id': [ignore],
        'entity_id': [not_empty, unicode],
        'entity_type': [not_empty, unicode],
        'task_type': [not_empty, unicode],
        'key': [not_empty, unicode],
        'value': [ignore_missing],
        'state': [ignore_missing],
        'last_updated': [ignore_missing],
        'error': [ignore_missing]
    }
    return schema

def default_vocabulary_schema():
    schema = {
        'id': [ignore_missing, unicode, vocabulary_id_exists],
        'name': [not_empty, unicode, vocabulary_name_validator],
        'tags': default_tags_schema(),
    }
    return schema

def default_create_vocabulary_schema():
    schema = default_vocabulary_schema()
    schema['id'] = [empty]
    return schema

def default_update_vocabulary_schema():
    schema = default_vocabulary_schema()
    schema['id'] = [ignore_missing, vocabulary_id_not_changed]
    schema['name'] = [ignore_missing, vocabulary_name_validator]
    return schema

def default_create_activity_schema():
    schema = {
        'id': [ignore],
        'timestamp': [ignore],
        'user_id': [not_missing, not_empty, unicode,
            convert_user_name_or_id_to_id],
        'object_id': [not_missing, not_empty, unicode, object_id_validator],
        # We don't bother to validate revision ID, since it's always created
        # internally by the activity_create() logic action function.
        'revision_id': [],
        'activity_type': [not_missing, not_empty, unicode,
            activity_type_exists],
        'data': [ignore_empty, ignore_missing],
    }
    return schema

def default_follow_user_schema():
    schema = {'id': [not_missing, not_empty, unicode,
        convert_user_name_or_id_to_id]}
    return schema

def default_follow_dataset_schema():
    schema = {'id': [not_missing, not_empty, unicode,
        convert_package_name_or_id_to_id]}
    return schema


def member_schema():
    schema = {
        'id': [group_id_exists, unicode],
        'username': [user_name_exists, unicode],
        'role': [role_exists, unicode],
    }
    return schema


def default_follow_group_schema():
    schema = {'id': [not_missing, not_empty, unicode,
        convert_group_name_or_id_to_id]}
    return schema


def default_package_list_schema():
    schema = {
        'limit': [ignore_missing, natural_number_validator],
        'offset': [ignore_missing, natural_number_validator],
        'page': [ignore_missing, is_positive_integer]
    }
    return schema


def default_pagination_schema():
    schema = {
        'limit': [ignore_missing, natural_number_validator],
        'offset': [ignore_missing, natural_number_validator]
    }
    return schema


def default_dashboard_activity_list_schema():
    schema = default_pagination_schema()
    schema['id'] = [unicode]
    return schema


def default_activity_list_schema():
    schema = default_pagination_schema()
    schema['id'] = [not_missing, unicode]
    return schema


def default_autocomplete_schema():
    schema = {
        'q': [not_missing, unicode],
        'limit': [ignore_missing, natural_number_validator]
    }
    return schema


def default_package_search_schema():
    schema = {
        'q': [ignore_missing, unicode],
        'fq': [ignore_missing, unicode],
        'rows': [ignore_missing, natural_number_validator],
        'sort': [ignore_missing, unicode],
        'start': [ignore_missing, natural_number_validator],
        'qf': [ignore_missing, unicode],
        'facet': [ignore_missing, unicode],
        'facet.mincount': [ignore_missing, natural_number_validator],
        'facet.limit': [ignore_missing, int_validator],
        'facet.field': [ignore_missing, convert_to_json_if_string,
            list_of_strings],
        'extras': [ignore_missing]  # Not used by Solr, but useful for extensions
    }
    return schema


def default_resource_search_schema():
    schema = {
        'query': [ignore_missing],  # string or list of strings
        'fields': [ignore_missing],  # dict of fields
        'order_by': [ignore_missing, unicode],
        'offset': [ignore_missing, natural_number_validator],
        'limit': [ignore_missing, natural_number_validator]
    }
    return schema


def create_schema_for_required_keys(keys):
    ''' helper function that creates a schema definition where
    each key from keys is validated against ``not_missing``.
    '''
    schema = dict([(x, [not_missing]) for x in keys])
    return schema
