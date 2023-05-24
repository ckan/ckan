# encoding: utf-8

from functools import wraps
import inspect

from six import text_type
import ckan.model
import ckan.plugins as plugins
from ckan.logic import get_validator


def validator_args(fn):
    u'''collect validator names from argument names
    and pass them to wrapped function'''

    args = inspect.getargspec(fn).args

    @wraps(fn)
    def wrapper():
        kwargs = {
            arg: get_validator(arg)
            for arg in args}
        return fn(**kwargs)

    return wrapper


@validator_args
def default_resource_schema(
        ignore_empty, unicode_safe, ignore, ignore_missing,
        remove_whitespace, if_empty_guess_format, clean_format, isodate,
        int_validator, extras_valid_json, keep_extras,
        resource_id_validator, resource_id_does_not_exist):
    return {
        'id': [ignore_empty, resource_id_validator,
               resource_id_does_not_exist, unicode_safe],
        'package_id': [ignore],
        'url': [ignore_missing, unicode_safe, remove_whitespace],
        'description': [ignore_missing, unicode_safe],
        'format': [if_empty_guess_format, ignore_missing, clean_format,
                   unicode_safe],
        'hash': [ignore_missing, unicode_safe],
        'state': [ignore],
        'position': [ignore],
        'name': [ignore_missing, unicode_safe],
        'resource_type': [ignore_missing, unicode_safe],
        'url_type': [ignore_missing, unicode_safe],
        'mimetype': [ignore_missing, unicode_safe],
        'mimetype_inner': [ignore_missing, unicode_safe],
        'cache_url': [ignore_missing, unicode_safe],
        'size': [ignore_missing, int_validator],
        'created': [ignore_missing, isodate],
        'last_modified': [ignore_missing, isodate],
        'cache_last_updated': [ignore_missing, isodate],
        'tracking_summary': [ignore_missing],
        'datastore_active': [ignore_missing],
        '__extras': [ignore_missing, extras_valid_json, keep_extras],
    }


@validator_args
def default_update_resource_schema(ignore):
    schema = default_resource_schema()
    return schema


@validator_args
def default_tags_schema(
        not_missing, not_empty, unicode_safe, tag_length_validator,
        tag_name_validator, ignore_missing, vocabulary_id_exists,
        ignore):
    return {
        'name': [not_missing,
                 not_empty,
                 unicode_safe,
                 tag_length_validator,
                 tag_name_validator,
                 ],
        'vocabulary_id': [ignore_missing,
                          unicode_safe,
                          vocabulary_id_exists],
        'revision_timestamp': [ignore],
        'state': [ignore],
        'display_name': [ignore],
    }


@validator_args
def default_create_tag_schema(
        not_missing, not_empty, unicode_safe, vocabulary_id_exists,
        tag_not_in_vocabulary, empty):
    schema = default_tags_schema()
    # When creating a tag via the tag_create() logic action function, a
    # vocabulary_id _must_ be given (you cannot create free tags via this
    # function).
    schema['vocabulary_id'] = [not_missing, not_empty, unicode_safe,
                               vocabulary_id_exists, tag_not_in_vocabulary]
    # You're not allowed to specify your own ID when creating a tag.
    schema['id'] = [empty]
    return schema


@validator_args
def default_create_package_schema(
        duplicate_extras_key, ignore, empty_if_not_sysadmin, ignore_missing,
        unicode_safe, package_id_does_not_exist, not_empty, name_validator,
        package_name_validator, if_empty_same_as, email_validator,
        package_version_validator, ignore_not_package_admin,
        boolean_validator, datasets_with_no_organization_cannot_be_private,
        empty, tag_string_convert, owner_org_validator, no_http):
    return {
        '__before': [duplicate_extras_key, ignore],
        'id': [empty_if_not_sysadmin, ignore_missing, unicode_safe,
               package_id_does_not_exist],
        'name': [
            not_empty, unicode_safe, name_validator, package_name_validator],
        'title': [if_empty_same_as("name"), unicode_safe],
        'author': [ignore_missing, unicode_safe],
        'author_email': [ignore_missing, unicode_safe, email_validator],
        'maintainer': [ignore_missing, unicode_safe],
        'maintainer_email': [ignore_missing, unicode_safe, email_validator],
        'license_id': [ignore_missing, unicode_safe],
        'notes': [ignore_missing, unicode_safe],
        'url': [ignore_missing, unicode_safe],
        'version': [ignore_missing, unicode_safe, package_version_validator],
        'state': [ignore_not_package_admin, ignore_missing],
        'type': [ignore_missing, unicode_safe],
        'owner_org': [owner_org_validator, unicode_safe],
        'log_message': [ignore_missing, unicode_safe, no_http],
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
            'id': [ignore_missing, unicode_safe],
            'name': [ignore_missing, unicode_safe],
            'title': [ignore_missing, unicode_safe],
            '__extras': [ignore],
        }
    }


@validator_args
def default_update_package_schema(
        ignore_missing, package_id_not_changed, name_validator,
        package_name_validator, unicode_safe, owner_org_validator):
    schema = default_create_package_schema()

    schema['resources'] = default_update_resource_schema()

    # Users can (optionally) supply the package id when updating a package, but
    # only to identify the package to be updated, they cannot change the id.
    schema['id'] = [ignore_missing, package_id_not_changed]

    # Supplying the package name when updating a package is optional (you can
    # supply the id to identify the package instead).
    schema['name'] = [ignore_missing, name_validator, package_name_validator,
                      unicode_safe]

    # Supplying the package title when updating a package is optional, if it's
    # not supplied the title will not be changed.
    schema['title'] = [ignore_missing, unicode_safe]

    schema['owner_org'] = [ignore_missing, owner_org_validator, unicode_safe]

    return schema


@validator_args
def default_show_package_schema(
        keep_extras, ignore_missing, clean_format, unicode_safe, not_empty):
    schema = default_create_package_schema()

    # Don't strip ids from package dicts when validating them.
    schema['id'] = []

    schema.update({
        'tags': {'__extras': [keep_extras]}})

    # Add several keys to the 'resources' subschema so they don't get stripped
    # from the resource dicts by validation.
    schema['resources'].update({
        'format': [ignore_missing, clean_format, unicode_safe],
        'created': [ignore_missing],
        'position': [not_empty],
        'last_modified': [],
        'cache_last_updated': [],
        'package_id': [],
        'size': [],
        'state': [],
        'mimetype': [],
        'cache_url': [],
        'name': [],
        'description': [],
        'mimetype_inner': [],
        'resource_type': [],
        'url_type': [],
    })

    schema.update({
        'state': [ignore_missing],
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

    # Add several keys that are missing from default_create_package_schema(),
    # so validation doesn't strip the keys from the package dicts.
    schema['metadata_created'] = []
    schema['metadata_modified'] = []
    schema['creator_user_id'] = []
    schema['num_resources'] = []
    schema['num_tags'] = []
    schema['organization'] = []
    schema['owner_org'] = []
    schema['private'] = []
    schema['tracking_summary'] = [ignore_missing]
    schema['license_title'] = []

    return schema


@validator_args
def default_group_schema(
        ignore_missing, unicode_safe, ignore, not_empty, name_validator,
        group_name_validator, package_id_or_name_exists,
        no_loops_in_hierarchy, ignore_not_group_admin):
    return {
        'id': [ignore_missing, unicode_safe],
        'name': [
            not_empty, unicode_safe, name_validator, group_name_validator],
        'title': [ignore_missing, unicode_safe],
        'description': [ignore_missing, unicode_safe],
        'image_url': [ignore_missing, unicode_safe],
        'image_display_url': [ignore_missing, unicode_safe],
        'type': [ignore_missing, unicode_safe],
        'state': [ignore_not_group_admin, ignore_missing],
        'created': [ignore],
        'is_organization': [ignore_missing],
        'approval_status': [ignore_missing, unicode_safe],
        'extras': default_extras_schema(),
        '__extras': [ignore],
        '__junk': [ignore],
        'packages': {
            "id": [not_empty, unicode_safe, package_id_or_name_exists],
            "title": [ignore_missing, unicode_safe],
            "name": [ignore_missing, unicode_safe],
            "__extras": [ignore]
        },
        'users': {
            "name": [not_empty, unicode_safe],
            "capacity": [ignore_missing],
            "__extras": [ignore]
        },
        'groups': {
            "name": [not_empty, no_loops_in_hierarchy, unicode_safe],
            "capacity": [ignore_missing],
            "__extras": [ignore]
        }
    }


@validator_args
def group_form_schema(
        not_empty, unicode_safe, ignore_missing, ignore):
    schema = default_group_schema()
    # schema['extras_validation'] = [duplicate_extras_key, ignore]
    schema['packages'] = {
        "name": [not_empty, unicode_safe],
        "title": [ignore_missing],
        "__extras": [ignore]
    }
    schema['users'] = {
        "name": [not_empty, unicode_safe],
        "capacity": [ignore_missing],
        "__extras": [ignore]
    }
    return schema


@validator_args
def default_update_group_schema(
        ignore_missing, group_name_validator, unicode_safe):
    schema = default_group_schema()
    schema["name"] = [ignore_missing, group_name_validator, unicode_safe]
    return schema


@validator_args
def default_show_group_schema(
        keep_extras, ignore_missing):
    schema = default_group_schema()

    # make default show schema behave like when run with no validation
    schema['num_followers'] = []
    schema['created'] = []
    schema['display_name'] = []
    schema['extras'] = {'__extras': [keep_extras]}
    schema['package_count'] = [ignore_missing]
    schema['packages'] = {'__extras': [keep_extras]}
    schema['state'] = []
    schema['users'] = {'__extras': [keep_extras]}

    return schema


@validator_args
def default_extras_schema(
        ignore, not_empty, extra_key_not_in_root_schema, unicode_safe,
        not_missing, ignore_missing):
    return {
        'id': [ignore],
        'key': [not_empty, extra_key_not_in_root_schema, unicode_safe],
        'value': [not_missing],
        'state': [ignore],
        'deleted': [ignore_missing],
        'revision_timestamp': [ignore],
        '__extras': [ignore],
    }


@validator_args
def default_relationship_schema(
        ignore_missing, unicode_safe, not_empty, one_of, ignore):
    return {
        'id': [ignore_missing, unicode_safe],
        'subject': [ignore_missing, unicode_safe],
        'object': [ignore_missing, unicode_safe],
        'type': [not_empty,
                 one_of(ckan.model.PackageRelationship.get_all_types())],
        'comment': [ignore_missing, unicode_safe],
        'state': [ignore],
    }


@validator_args
def default_create_relationship_schema(
        empty, not_empty, unicode_safe, package_id_or_name_exists):
    schema = default_relationship_schema()
    schema['id'] = [empty]
    schema['subject'] = [not_empty, unicode_safe, package_id_or_name_exists]
    schema['object'] = [not_empty, unicode_safe, package_id_or_name_exists]

    return schema


@validator_args
def default_update_relationship_schema(
        ignore_missing, package_id_not_changed):
    schema = default_relationship_schema()
    schema['id'] = [ignore_missing, package_id_not_changed]

    # Todo: would like to check subject, object & type haven't changed, but
    # no way to do this in schema
    schema['subject'] = [ignore_missing]
    schema['object'] = [ignore_missing]
    schema['type'] = [ignore_missing]

    return schema


@validator_args
def default_user_schema(
        ignore_missing, unicode_safe, name_validator, user_name_validator,
        user_password_validator, user_password_not_empty, email_is_unique,
        ignore_not_sysadmin, not_empty, email_validator,
        user_about_validator, ignore, boolean_validator, json_object):
    return {
        'id': [ignore_missing, unicode_safe],
        'name': [
            not_empty, name_validator, user_name_validator, unicode_safe],
        'fullname': [ignore_missing, unicode_safe],
        'password': [user_password_validator, user_password_not_empty,
                     ignore_missing, unicode_safe],
        'password_hash': [ignore_missing, ignore_not_sysadmin, unicode_safe],
        'email': [not_empty, email_validator, email_is_unique, unicode_safe],
        'about': [ignore_missing, user_about_validator, unicode_safe],
        'created': [ignore],
        'sysadmin': [ignore_missing, ignore_not_sysadmin],
        'apikey': [ignore],
        'reset_key': [ignore],
        'activity_streams_email_notifications': [ignore_missing,
                                                 boolean_validator],
        'state': [ignore_missing, ignore_not_sysadmin],
        'image_url': [ignore_missing, unicode_safe],
        'image_display_url': [ignore_missing, unicode_safe],
        'plugin_extras': [ignore_missing, json_object, ignore_not_sysadmin],
    }


@validator_args
def user_new_form_schema(
        unicode_safe, user_both_passwords_entered,
        user_password_validator, user_passwords_match):
    schema = default_user_schema()

    schema['password1'] = [text_type, user_both_passwords_entered,
                           user_password_validator, user_passwords_match]
    schema['password2'] = [text_type]

    return schema


@validator_args
def user_edit_form_schema(
        ignore_missing, unicode_safe, user_password_validator,
        user_passwords_match):
    schema = default_user_schema()

    schema['password'] = [ignore_missing]
    schema['password1'] = [ignore_missing, unicode_safe,
                           user_password_validator, user_passwords_match]
    schema['password2'] = [ignore_missing, unicode_safe]

    return schema


@validator_args
def default_update_user_schema(
        ignore_missing, name_validator, user_name_validator,
        unicode_safe, user_password_validator, email_is_unique,
        not_empty, email_validator):
    schema = default_user_schema()

    schema['name'] = [
        ignore_missing, name_validator, user_name_validator, unicode_safe]
    schema['password'] = [
        user_password_validator, ignore_missing, unicode_safe]

    return schema


@validator_args
def default_generate_apikey_user_schema(
        not_empty, unicode_safe):
    schema = default_update_user_schema()

    schema['apikey'] = [not_empty, unicode_safe]
    return schema


@validator_args
def default_user_invite_schema(
        not_empty, email_validator, email_is_unique):
    return {
        'email': [not_empty, email_validator, email_is_unique, text_type],
        'group_id': [not_empty],
        'role': [not_empty],
    }


@validator_args
def default_task_status_schema(
        ignore, not_empty, unicode_safe, ignore_missing):
    return {
        'id': [ignore],
        'entity_id': [not_empty, unicode_safe],
        'entity_type': [not_empty, unicode_safe],
        'task_type': [not_empty, unicode_safe],
        'key': [not_empty, unicode_safe],
        'value': [ignore_missing],
        'state': [ignore_missing],
        'last_updated': [ignore_missing],
        'error': [ignore_missing]
    }


@validator_args
def default_vocabulary_schema(
        ignore_missing, unicode_safe, vocabulary_id_exists,
        not_empty, vocabulary_name_validator):
    return {
        'id': [ignore_missing, unicode_safe, vocabulary_id_exists],
        'name': [not_empty, unicode_safe, vocabulary_name_validator],
        'tags': default_tags_schema(),
    }


@validator_args
def default_create_vocabulary_schema(
        empty):
    schema = default_vocabulary_schema()
    schema['id'] = [empty]
    return schema


@validator_args
def default_update_vocabulary_schema(
        ignore_missing, vocabulary_id_not_changed,
        vocabulary_name_validator):
    schema = default_vocabulary_schema()
    schema['id'] = [ignore_missing, vocabulary_id_not_changed]
    schema['name'] = [ignore_missing, vocabulary_name_validator]
    return schema


@validator_args
def default_create_activity_schema(
        ignore, not_missing, not_empty, unicode_safe,
        convert_user_name_or_id_to_id, object_id_validator,
        activity_type_exists, ignore_empty, ignore_missing):
    return {
        'id': [ignore],
        'timestamp': [ignore],
        'user_id': [not_missing, not_empty, unicode_safe,
                    convert_user_name_or_id_to_id],
        'object_id': [
            not_missing, not_empty, unicode_safe, object_id_validator],
        'activity_type': [not_missing, not_empty, unicode_safe,
                          activity_type_exists],
        'data': [ignore_empty, ignore_missing],
    }


@validator_args
def default_follow_user_schema(
        not_missing, not_empty, unicode_safe, convert_user_name_or_id_to_id,
        ignore_missing):
    return {
        'id': [not_missing, not_empty, unicode_safe,
               convert_user_name_or_id_to_id],
        'q': [ignore_missing]
    }


@validator_args
def default_follow_dataset_schema(
        not_missing, not_empty, unicode_safe,
        convert_package_name_or_id_to_id):
    return {
        'id': [not_missing, not_empty, unicode_safe,
               convert_package_name_or_id_to_id]
    }


@validator_args
def member_schema(
        not_missing, group_id_or_name_exists, unicode_safe,
        user_id_or_name_exists, role_exists):
    return {
        'id': [not_missing, group_id_or_name_exists, unicode_safe],
        'username': [not_missing, user_id_or_name_exists, unicode_safe],
        'role': [not_missing, role_exists, unicode_safe],
    }


@validator_args
def default_follow_group_schema(
        not_missing, not_empty, unicode_safe,
        convert_group_name_or_id_to_id):
    return {
        'id': [not_missing, not_empty, unicode_safe,
               convert_group_name_or_id_to_id]
    }


@validator_args
def default_package_list_schema(
        ignore_missing, natural_number_validator, is_positive_integer):
    return {
        'limit': [ignore_missing, natural_number_validator],
        'offset': [ignore_missing, natural_number_validator],
        'page': [ignore_missing, is_positive_integer]
    }


@validator_args
def default_pagination_schema(ignore_missing, natural_number_validator):
    return {
        'limit': [ignore_missing, natural_number_validator],
        'offset': [ignore_missing, natural_number_validator]
    }


@validator_args
def default_dashboard_activity_list_schema(
        configured_default, natural_number_validator,
        limit_to_configured_maximum):
    schema = default_pagination_schema()
    schema['limit'] = [
        configured_default('ckan.activity_list_limit', 31),
        natural_number_validator,
        limit_to_configured_maximum('ckan.activity_list_limit_max', 100)]
    return schema


@validator_args
def default_activity_list_schema(
        not_missing, unicode_safe, configured_default,
        natural_number_validator, limit_to_configured_maximum,
        ignore_missing, boolean_validator, ignore_not_sysadmin):
    schema = default_pagination_schema()
    schema['id'] = [not_missing, unicode_safe]
    schema['limit'] = [
        configured_default('ckan.activity_list_limit', 31),
        natural_number_validator,
        limit_to_configured_maximum('ckan.activity_list_limit_max', 100)]
    schema['include_hidden_activity'] = [
        ignore_missing, ignore_not_sysadmin, boolean_validator]
    return schema


@validator_args
def default_autocomplete_schema(
        not_missing, unicode_safe, ignore_missing, natural_number_validator):
    return {
        'q': [not_missing, unicode_safe],
        'ignore_self': [ignore_missing],
        'limit': [ignore_missing, natural_number_validator]
    }


@validator_args
def default_package_search_schema(
        ignore_missing, unicode_safe, list_of_strings,
        natural_number_validator, int_validator, convert_to_json_if_string,
        convert_to_list_if_string, limit_to_configured_maximum, default):
    return {
        'q': [ignore_missing, unicode_safe],
        'fl': [ignore_missing, convert_to_list_if_string],
        'fq': [ignore_missing, unicode_safe],
        'rows': [default(10), natural_number_validator,
                 limit_to_configured_maximum('ckan.search.rows_max', 1000)],
        'sort': [ignore_missing, unicode_safe],
        'start': [ignore_missing, natural_number_validator],
        'qf': [ignore_missing, unicode_safe],
        'facet': [ignore_missing, unicode_safe],
        'facet.mincount': [ignore_missing, natural_number_validator],
        'facet.limit': [ignore_missing, int_validator],
        'facet.field': [ignore_missing, convert_to_json_if_string,
                        list_of_strings],
        'extras': [ignore_missing]  # Not used by Solr,
                                    # but useful for extensions
    }


@validator_args
def default_resource_search_schema(
        ignore_missing, unicode_safe, natural_number_validator):
    schema = {
        'query': [ignore_missing],  # string or list of strings
        'fields': [ignore_missing],  # dict of fields
        'order_by': [ignore_missing, unicode_safe],
        'offset': [ignore_missing, natural_number_validator],
        'limit': [ignore_missing, natural_number_validator]
    }
    return schema


def create_schema_for_required_keys(keys):
    ''' helper function that creates a schema definition where
    each key from keys is validated against ``not_missing``.
    '''
    not_missing = get_validator('not_missing')
    return {x: [not_missing] for x in keys}


def default_create_resource_view_schema(resource_view):
    if resource_view.info().get('filterable'):
        return default_create_resource_view_schema_filtered()
    return default_create_resource_view_schema_unfiltered()


@validator_args
def default_create_resource_view_schema_unfiltered(
        not_empty, resource_id_exists, unicode_safe, ignore_missing, empty):
    return {
        'resource_id': [not_empty, resource_id_exists],
        'title': [not_empty, unicode_safe],
        'description': [ignore_missing, unicode_safe],
        'view_type': [not_empty, unicode_safe],
        '__extras': [empty],
    }


@validator_args
def default_create_resource_view_schema_filtered(
        ignore_missing, convert_to_list_if_string,
        filter_fields_and_values_should_have_same_length,
        filter_fields_and_values_exist_and_are_valid):
    schema = default_create_resource_view_schema_unfiltered()
    schema['filter_fields'] = [
        ignore_missing,
        convert_to_list_if_string,
        filter_fields_and_values_should_have_same_length,
        filter_fields_and_values_exist_and_are_valid]
    schema['filter_values'] = [ignore_missing, convert_to_list_if_string]
    return schema


def default_update_resource_view_schema(resource_view):
    schema = default_create_resource_view_schema(resource_view)
    schema.update(default_update_resource_view_schema_changes())
    return schema


@validator_args
def default_update_resource_view_schema_changes(
        not_missing, not_empty, unicode_safe, resource_id_exists, ignore,
        ignore_missing):
    return {
        'id': [not_missing, not_empty, unicode_safe],
        'resource_id': [ignore_missing, resource_id_exists],
        'title': [ignore_missing, unicode_safe],
        'view_type': [ignore],  # cannot change after create
        'package_id': [ignore]
    }


@validator_args
def default_update_configuration_schema(
        unicode_safe, is_positive_integer, ignore_missing):
    return {
        'ckan.site_title': [ignore_missing, unicode_safe],
        'ckan.site_logo': [ignore_missing, unicode_safe],
        'ckan.site_url': [ignore_missing, unicode_safe],
        'ckan.site_description': [ignore_missing, unicode_safe],
        'ckan.site_about': [ignore_missing, unicode_safe],
        'ckan.site_intro_text': [ignore_missing, unicode_safe],
        'ckan.site_custom_css': [ignore_missing, unicode_safe],
        'ckan.theme': [ignore_missing, unicode_safe],
        'ckan.homepage_style': [ignore_missing, is_positive_integer],
        'logo_upload': [ignore_missing, unicode_safe],
        'clear_logo_upload': [ignore_missing, unicode_safe],
    }


def update_configuration_schema():
    '''
    Returns the schema for the config options that can be edited during runtime

    By default these are the keys of the
    :py:func:`ckan.logic.schema.default_update_configuration_schema`.
    Extensions can add or remove keys from this schema using the
    :py:meth:`ckan.plugins.interfaces.IConfigurer.update_config_schema`
    method.

    These configuration options can be edited during runtime via the web
    interface or using
    the :py:func:`ckan.logic.action.update.config_option_update` API call.

    :returns: a dictionary mapping runtime-editable configuration option keys
      to lists of validator and converter functions to be applied to those
      keys
    :rtype: dictionary
    '''

    schema = default_update_configuration_schema()
    for plugin in plugins.PluginImplementations(plugins.IConfigurer):
        if hasattr(plugin, 'update_config_schema'):
            schema = plugin.update_config_schema(schema)

    return schema


@validator_args
def job_list_schema(ignore_missing, list_of_strings):
    return {
        u'queues': [ignore_missing, list_of_strings],
    }


@validator_args
def job_clear_schema(ignore_missing, list_of_strings):
    return {
        u'queues': [ignore_missing, list_of_strings],
    }


@validator_args
def default_create_api_token_schema(
        not_empty, unicode_safe,
        ignore_missing, json_object, ignore_not_sysadmin):
    return {
        u'name': [not_empty, unicode_safe],
        u'user': [not_empty, unicode_safe],
        u'plugin_extras': [ignore_missing, json_object, ignore_not_sysadmin],
    }


@validator_args
def package_revise_schema(
        ignore_missing, list_of_strings,
        collect_prefix_validate, json_or_string,
        json_list_or_string, dict_only):
    return {
        u'__before': [
            collect_prefix_validate(
                u'match__', u'json_or_string'),
            collect_prefix_validate(
                u'update__', u'json_or_string')],
        u'match': [
            ignore_missing, json_or_string, dict_only],
        u'filter': [
            ignore_missing, json_list_or_string, list_of_strings],
        u'update': [
            ignore_missing, json_or_string, dict_only],
        u'include': [
            ignore_missing, json_list_or_string, list_of_strings],
        # collect_prefix moves values to these, always dicts:
        u'match__': [],
        u'update__': [],
    }
