# encoding: utf-8

'''
Functions used by the helper function compare_pkg_dicts() to analyze
the differences between two versions of a dataset.
'''
from helpers import url_for
import logging
log = logging.getLogger(__name__)


def _extras_to_dict(extras_list):
    '''
    Takes a list of dictionaries with the following format:
    [
        {
            "key": <key_0>,
            "value": <value_0>
        },
        ...,
        {
            "key": <key_n>,
            "value": <value_n>
        }
    ]
    and converts it into a single dictionary with the following
    format:
    {
        key_0: value_0,
        ...,
        key_n: value_n

    }
    '''
    ret_dict = {}
    # the extras_list is a list of dictionaries
    for dict in extras_list:
        ret_dict[dict['key']] = dict['value']

    return ret_dict


def _check_resource_changes(change_list, original, new, new_pkg,
                            old_activity_id):
    '''
    Checks whether a dataset's resources have changed - whether new ones have
    been uploaded, existing ones have been deleted, or existing ones have
    been edited. For existing resources, checks whether their names, formats,
    and/or descriptions have changed, as well as whether a new file has been
    uploaded for the resource.
    '''

    # make a set of the resource IDs present in original and new
    original_resource_set = set()
    original_resource_dict = {}
    new_resource_set = set()
    new_resource_dict = {}
    s = u""

    for resource in original['resources']:
        original_resource_set.add(resource['id'])
        original_resource_dict[resource['id']] = {
            u'name': resource['name'],
            u'url': resource['url'],
            u'description': resource['description'],
            u'format': resource['format']}

    for resource in new['resources']:
        new_resource_set.add(resource['id'])
        new_resource_dict[resource['id']] = {
            u'name': resource['name'],
            u'url': resource['url'],
            u'description': resource['description'],
            u'format': resource['format']}

    # get the IDs of the resources that have been added between the versions
    new_resources = list(new_resource_set - original_resource_set)
    for resource_id in new_resources:
        change_list.append({u'type': u'new_resource',
                            u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'],
                            u'resource_name':
                            new_resource_dict[resource_id]['name'],
                            u'resource_id': resource_id})

    # get the IDs of resources that have been deleted between versions
    deleted_resources = list(original_resource_set - new_resource_set)
    for resource_id in deleted_resources:
        change_list.append({u'type': u'delete_resource',
                            u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'],
                            u'resource_id': resource_id,
                            u'resource_name':
                            original_resource_dict[resource_id]['name'],
                            u'old_activity_id': old_activity_id})

    # now check the resources that are in both and see if any
    # have been changed
    resources = new_resource_set.intersection(original_resource_set)
    for resource_id in resources:
        original_metadata = original_resource_dict[resource_id]
        new_metadata = new_resource_dict[resource_id]

        if original_metadata['name'] != new_metadata['name']:
            change_list.append({u'type': u'resource_name',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'old_pkg_id': original['id'],
                                u'new_pkg_id': new['id'],
                                u'resource_id': resource_id,
                                u'old_resource_name':
                                original_resource_dict[resource_id]['name'],
                                u'new_resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'old_activity_id': old_activity_id})

        # you can't remove a format, but if a resource's format isn't
        # recognized, it won't have one set

        # if a format was not originally set and the user set one
        if not original_metadata['format'] and new_metadata['format']:
            change_list.append({u'type': u'resource_format',
                                u'method': u'add',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'org_id': new['organization']['id'],
                                u'format': new_metadata['format']})

        # if both versions have a format but the format changed
        elif original_metadata['format'] != new_metadata['format']:
            change_list.append({u'type': u'resource_format',
                                u'method': u'change',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'org_id': new['organization']['id'],
                                u'old_format': original_metadata['format'],
                                u'new_format': new_metadata['format']})

        # if the description changed
        if not original_metadata['description'] and \
                new_metadata['description']:
            change_list.append({u'type': u'resource_desc',
                                u'method': u'add',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'new_desc': new_metadata['description']})

        # if there was a description but the user removed it
        elif original_metadata['description'] and \
                not new_metadata['description']:
            change_list.append({u'type': u'resource_desc',
                                u'method': u'remove',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name']})

        # if both have descriptions but they are different
        elif original_metadata['description'] != new_metadata['description']:
            change_list.append({u'type': u'resource_desc',
                                u'method': u'change',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'new_desc': new_metadata['description'],
                                u'old_desc': original_metadata['description']})

        # check if the user uploaded a new file
        # TODO: use regular expressions to determine the actual name of the
        # new and old files
        if original_metadata['url'] != new_metadata['url']:
            change_list.append({u'type': u'new_file',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name']})


def _check_metadata_changes(change_list, original, new, new_pkg):
    '''
    Checks whether a dataset's metadata fields (fields in its package
    dictionary not including resources) have changed between two consecutive
    versions and puts a list of formatted summaries of these changes in
    change_list.
    '''
    # if the title has changed
    if original['title'] != new['title']:
        _title_change(change_list, original, new)

    # if the owner organization changed
    if original['owner_org'] != new['owner_org']:
        _org_change(change_list, original, new, new_pkg)

    # if the maintainer of the dataset changed
    if original['maintainer'] != new['maintainer']:
        _maintainer_change(change_list, original, new, new_pkg)

    # if the maintainer email of the dataset changed
    if original['maintainer_email'] != new['maintainer_email']:
        _maintainer_email_change(change_list, original, new, new_pkg)

    # if the author of the dataset changed
    if original['author'] != new['author']:
        _author_change(change_list, original, new, new_pkg)

    # if the author email of the dataset changed
    if original['author_email'] != new['author_email']:
        _author_email_change(change_list, original, new, new_pkg)

    # if the visibility of the dataset changed
    if original['private'] != new['private']:
        change_list.append({u'type': u'private', u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'],
                            u'new':
                            u'Private' if bool(new['private'])
                            else u'Public'})

    # if the description of the dataset changed
    if original['notes'] != new['notes']:
        _description_change(change_list, original, new, new_pkg)

    # make sets out of the tags for each dataset
    original_tags = set([tag['name'] for tag in original['tags']])
    new_tags = set([tag['name'] for tag in new['tags']])
    # if the tags have changed
    if original_tags != new_tags:
        _tag_change(change_list, new_tags, original_tags, new_pkg)

    # if the license has changed
    if original['license_title'] != new['license_title']:
        _license_change(change_list, original, new, new_pkg)

    # if the name of the dataset has changed
    # this is only visible to the user via the dataset's URL,
    # so display the change using that
    if original['name'] != new['name']:
        _name_change(change_list, original, new, new_pkg)

    # if the source URL (metadata value, not the actual URL of the dataset)
    # has changed
    if original['url'] != new['url']:
        _source_url_change(change_list, original, new, new_pkg)

    # if the user-provided version has changed
    if original['version'] != new['version']:
        _version_change(change_list, original, new, new_pkg)

    # check whether fields added by extensions or custom fields
    # (in the "extras" field) have been changed

    _extension_fields(change_list, original, new, new_pkg)
    _extra_fields(change_list, original, new, new_pkg)


def _title_change(change_list, original, new):
    '''
    Appends a summary of a change to a dataset's title between two versions
    (original and new) to change_list.
    '''
    change_list.append({u'type': u'title', u'id': new['name'],
                        u'new_title': new['title'],
                        u'original_title': original['title']})


def _org_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's organization between
    two versions (original and new) to change_list.
    '''
    change_list.append({u'type': u'org', u'pkg_id': new_pkg['pkg_id'],
                        u'title': new_pkg['title'],
                        u'original_org_id': original['organization']['id'],
                        u'original_org_title':
                        original['organization']['title'],
                        u'new_org_id': new['organization']['id'],
                        u'new_org_title': new['organization']['title']})


def _maintainer_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's maintainer field between two
    versions (original and new) to change_list.
    '''
    # if the original dataset had a maintainer
    if original['maintainer'] and new['maintainer']:
        change_list.append({u'type': u'maintainer', u'method': u'change',
                            u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'], u'new_maintainer':
                            new['maintainer'], u'old_maintainer':
                            original['maintainer']})
    # if they removed the maintainer
    elif not new['maintainer']:
        change_list.append({u'type': u'maintainer', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'method': u'remove'})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'maintainer', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'new_maintainer': new['maintainer'],
                            u'method': u'add'})


def _maintainer_email_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's maintainer e-mail address
    field between two versions (original and new) to change_list.
    '''
    # if the original dataset had a maintainer email
    if original['maintainer_email'] and new['maintainer_email']:
        change_list.append({u'type': u'maintainer_email', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'new_maintainer_email': new['maintainer_email'],
                            u'old_maintainer_email':
                            original['maintainer_email'],
                            u'method': u'change'})
    # if they removed the maintainer email
    elif not new['maintainer_email']:
        change_list.append({u'type': u'maintainer_email', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'method': u'remove'})
    # if there wasn't one there before e
    else:
        change_list.append({u'type': u'maintainer_email', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'new_maintainer_email': new['maintainer_email'],
                            u'method': u'add'})


def _author_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's author field between two
    versions (original and new) to change_list.
    '''
    # if the original dataset had an author
    if original['author'] and new['author']:
        change_list.append({u'type': u'author', u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'], u'new_author':
                            new['author'], u'old_author': original['author'],
                            u'method': u'change'})
    # if they removed the author
    elif not new['author']:
        change_list.append({u'type': u'author', u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'], u'method': u'remove'})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'author', u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'], u'new_author':
                            new['author'], u'method': u'add'})


def _author_email_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's author e-mail address field
    between two versions (original and new) to change_list.
    '''
    if original['author_email'] and new['author_email']:
        change_list.append({u'type': u'author_email', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'new_author_email': new['author_email'],
                            u'old_author_email': original['author_email'],
                            u'method': u'change'})
    # if they removed the author
    elif not new['author_email']:
        change_list.append({u'type': u'author_email', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'method': u'remove'})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'author_email', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'new_author_email': new['author_email'],
                            u'method': u'add'})


def _description_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's description between two
    versions (original and new) to change_list.
    '''
    # if the original dataset had a description
    if original['notes'] and new['notes']:
        change_list.append({u'type': u'description', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'new_desc': new['notes'],
                            u'old_desc': original['notes'],
                            u'method': u'change'})
    elif not new['notes']:
        change_list.append({u'type': u'description', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'method': u'remove'})
    else:
        change_list.append({u'type': u'description', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'new_desc': new['notes'], u'method': u'add'})


def _tag_change(change_list, new_tags, original_tags, new_pkg):
    '''
    Appends a summary of a change to a dataset's tag list between two
    versions (original and new) to change_list.
    '''
    deleted_tags = original_tags - new_tags
    deleted_tags_list = list(deleted_tags)
    if len(deleted_tags) == 1:
        change_list.append({u'type': u'tags', u'method': u'remove1', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'tag': deleted_tags_list[0]})
    elif len(deleted_tags) > 1:
        change_list.append({u'type': u'tags', u'method': u'remove2', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'tags': deleted_tags_list})

    added_tags = new_tags - original_tags
    added_tags_list = list(added_tags)
    if len(added_tags) == 1:
        change_list.append({u'type': u'tags', u'method': u'add1', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'tag': added_tags_list[0]})
    elif len(added_tags) > 1:
        change_list.append({u'type': u'tags', u'method': u'add2', u'pkg_id':
                            new_pkg['pkg_id'], u'title': new_pkg['title'],
                            u'tags': added_tags_list})


def _license_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's license between two versions
    (original and new) to change_list.
    '''
    original_license_url = u""
    new_license_url = u""
    # if the license has a URL
    if u'license_url' in original and original['license_url']:
        original_license_url = original['license_url']
    if u'license_url' in new and new['license_url']:
        new_license_url = new['license_url']
    change_list.append({u'type': u'license', u'pkg_id': new_pkg['pkg_id'],
                        u'title': new_pkg['title'],
                        u'old_url': original_license_url,
                        u'new_url': new_license_url, u'new_title':
                        new['license_title'], u'old_title':
                        original['license_title']})


def _name_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's name (and thus the URL it
    can be accessed at) between two versions (original and new) to
    change_list.
    '''
    change_list.append({u'type': u'name', u'pkg_id': new_pkg['pkg_id'],
                        u'title': new_pkg['title'], u'old_name':
                        original['name'], u'new_name': new['name']})


def _source_url_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's source URL (metadata field,
    not its actual URL in the datahub) between two versions (original and
    new) to change_list.
    '''
    # if both old and new versions have source URLs
    if original['url'] and new['url']:
        change_list.append({u'type': u'source_url', u'method': u'change',
                            u'pkg_id': new_pkg['pkg_id'], u'title':
                            new_pkg['title'], u'new_url': new['url'],
                            u'old_url': original['url']})
    # if the user removed the source URL
    elif not new['url']:
        change_list.append({u'type': u'source_url', u'method': u'remove',
                            u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'],
                            u'old_url': original['url']})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'source_url', u'method': u'add',
                            u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'],
                            u'new_url': new['url']})


def _version_change(change_list, original, new, new_pkg):
    '''
    Appends a summary of a change to a dataset's version field (inputted
    by the user, not from version control) between two versions (original
    and new) to change_list.
    '''
    # if both old and new versions have version numbers
    if original['version'] and new['version']:
        change_list.append({u'type': u'version', u'method': u'change',
                            u'pkg_id': new_pkg['pkg_id'], u'title':
                            new_pkg['title'], u'old_version':
                            original['version'], u'new_version':
                            new['version']})
    # if the user removed the version number
    elif not new['version']:
        change_list.append({u'type': u'version', u'method': u'remove',
                            u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title']})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'version', u'method': u'add',
                            u'pkg_id': new_pkg['pkg_id'],
                            u'title': new_pkg['title'],
                            u'new_version': new['version']})


def _extension_fields(change_list, original, new, new_pkg):
    '''
    Checks whether any fields that have been added to the package
    dictionaries by CKAN extensions have been changed between versions.
    If there have been any changes between the two versions (original and
    new), a general summary of the change is appended to change_list. This
    function does not produce summaries for fields added or deleted by
    extensions, since these changes are not triggered by the user in the web
    interface or API.
    '''
    # list of the default metadata fields for a dataset
    # any fields that are not part of this list are custom fields added by a
    # user or extension
    fields = [
        u'owner_org', u'maintainer', u'maintainer_email',
        u'relationships_as_object', u'private', u'num_tags',
        u'id', u'metadata_created', u'metadata_modified',
        u'author', u'author_email', u'state', u'version',
        u'license_id', u'type', u'resources', u'num_resources',
        u'tags', u'title', u'groups', u'creator_user_id',
        u'relationships_as_subject', u'name', u'isopen', u'url',
        u'notes', u'license_title', u'extras',
        u'license_url', u'organization', u'revision_id'
    ]
    fields_set = set(fields)

    # if there are any fields from extensions that are in the new dataset and
    # have been updated, print a generic message stating that
    original_set = set(original.keys())
    new_set = set(new.keys())

    # set of additional fields in the new dictionary
    addl_fields_new = new_set - fields_set
    # set of additional fields in the original dictionary
    addl_fields_original = original_set - fields_set
    # set of additional fields in both
    addl_fields = addl_fields_new.intersection(addl_fields_original)

    # do NOT display a change if any additional fields have been
    # added or deleted, since that is not a change made by the user
    # from the web interface

    # if additional fields have been changed
    addl_fields_list = list(addl_fields)
    for field in addl_fields_list:
        if original[field] != new[field]:
            change_list.append({u'type': u'extension_fields',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'field_name': field,
                                u'new_field': new[field]})


def _extra_fields(change_list, original, new, new_pkg):
    '''
    Checks whether a user has added, removed, or changed any custom fields
    from the web interface (or API?) and appends a summary of each change to
    change_list.
    '''
    s = u""
    if u'extras' in new:
        extra_fields_new = _extras_to_dict(new['extras'])
        extra_new_set = set(extra_fields_new.keys())

        # if the original version has extra fields, we need
        # to compare the new version'sextras to the original ones
        if u'extras' in original:
            extra_fields_original = _extras_to_dict(original['extras'])
            extra_original_set = set(extra_fields_original.keys())

            # if some fields were added
            new_fields = list(extra_new_set - extra_original_set)
            if len(new_fields) == 1:
                if extra_fields_new[new_fields[0]]:
                    change_list.append({u'type': u'custom_fields',
                                        u'method': u'add1',
                                        u'pkg_id': new_pkg['pkg_id'],
                                        u'title': new_pkg['title'],
                                        u'field_name': new_fields[0],
                                        u'field_val':
                                        extra_fields_new[new_fields[0]]})
                else:
                    change_list.append({u'type': u'custom_fields',
                                        u'method': u'add2',
                                        u'pkg_id': new_pkg['pkg_id'],
                                        u'title': new_pkg['title'],
                                        u'field_name': new_fields[0]})
            elif len(new_fields) > 1:
                change_list.append({u'type': u'custom_fields',
                                    u'method': u'add3',
                                    u'pkg_id': new_pkg['pkg_id'],
                                    u'title': new_pkg['title'],
                                    u'fields': new_fields,
                                    u'field_vals': extra_fields_new})

            # if some fields were deleted
            deleted_fields = list(extra_original_set - extra_new_set)
            if len(deleted_fields) == 1:
                change_list.append({u'type': u'custom_fields',
                                    u'method': u'remove1',
                                    u'pkg_id': new_pkg['pkg_id'],
                                    u'title': new_pkg['title'],
                                    u'field_name': deleted_fields[0]})
            elif len(deleted_fields) > 1:
                change_list.append({u'type': u'custom_fields',
                                    u'method': u'remove2',
                                    u'pkg_id': new_pkg['pkg_id'],
                                    u'title': new_pkg['title'],
                                    u'fields': deleted_fields})

            # if some existing fields were changed
            # list of extra fields in both the original and new versions
            extra_fields = list(extra_new_set.intersection(extra_original_set))
            for field in extra_fields:
                if extra_fields_original[field] != extra_fields_new[field]:
                    if extra_fields_original[field]:
                        change_list.append({u'type': u'custom_fields',
                                            u'method': u'change1',
                                            u'pkg_id': new_pkg['pkg_id'],
                                            u'title': new_pkg['title'],
                                            u'field_name': field,
                                            u'field_val_old':
                                            extra_fields_original[field],
                                            u'field_val_new':
                                            extra_fields_new[field]})
                    else:
                        change_list.append({u'type': u'custom_fields',
                                            u'method': u'change2',
                                            u'pkg_id': new_pkg['pkg_id'],
                                            u'title': new_pkg['title'],
                                            u'field_name': field,
                                            u'field_val_new':
                                            extra_fields_new[field]})

        # if the original version didn't have an extras field,
        # the user could only have added a field (not changed or deleted)
        else:
            new_fields = list(extra_new_set)
            if len(new_fields) == 1:
                if extra_fields_new[new_fields[0]]:
                    change_list.append({u'type': u'custom_fields',
                                        u'method': u'add1',
                                        u'pkg_id': new_pkg['pkg_id'],
                                        u'title': new_pkg['title'],
                                        u'field_name': new_fields[0],
                                        u'field_val':
                                        extra_fields_new[new_fields[0]]})
                else:
                    change_list.append({u'type': u'custom_fields',
                                        u'method': u'add2',
                                        u'pkg_id': new_pkg['pkg_id'],
                                        u'title': new_pkg['title'],
                                        u'field_name': new_fields[0]})

            elif len(new_fields) > 1:
                change_list.append({u'type': u'custom_fields',
                                    u'method': u'add3',
                                    u'pkg_id': new_pkg['pkg_id'],
                                    u'title': new_pkg['title'],
                                    u'fields': new_fields,
                                    u'field_vals': extra_fields_new})

    elif u'extras' in original:
        deleted_fields = _extras_to_dict(original['extras']).keys()
        if len(deleted_fields) == 1:
            change_list.append({u'type': u'custom_fields',
                                u'method': u'remove1',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'field_name': deleted_fields[0]})
        elif len(deleted_fields) > 1:
            change_list.append({u'type': u'custom_fields',
                                u'method': u'remove2',
                                u'pkg_id': new_pkg['pkg_id'],
                                u'title': new_pkg['title'],
                                u'fields': deleted_fields})
