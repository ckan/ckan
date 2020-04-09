# encoding: utf-8

'''
Functions for generating a list of differences between two versions of a
dataset
'''

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


def check_resource_changes(change_list, old, new, old_activity_id):
    '''
    Compares two versions of a dataset and records the changes between them
    (just the resources) in change_list. e.g. resources that are added, changed
    or deleted. For existing resources, checks whether their names, formats,
    and/or descriptions have changed, as well as whether the url changed (e.g.
    a new file has been uploaded for the resource).
    '''

    # list of default fields in a resource's metadata dictionary - used
    # later to ensure that we don't count changes to default fields as changes
    # to extra fields
    fields = [
        u'package_id', u'url', u'revision_id', u'description',
        u'format', u'hash', u'name', u'resource_type',
        u'mimetype', u'mimetype_inner', u'cache_url',
        u'size', u'created', u'last_modified', u'metadata_modified',
        u'cache_last_updated', u'upload', u'position'
    ]
    default_fields_set = set(fields)

    # make a set of the resource IDs present in old and new
    old_resource_set = set()
    old_resource_dict = {}
    new_resource_set = set()
    new_resource_dict = {}

    for resource in old['resources']:
        old_resource_set.add(resource['id'])
        old_resource_dict[resource['id']] = {
            key: value for (key, value) in resource.items() if key != u'id'}

    for resource in new['resources']:
        new_resource_set.add(resource['id'])
        new_resource_dict[resource['id']] = {
            key: value for (key, value) in resource.items() if key != u'id'}

    # get the IDs of the resources that have been added between the versions
    new_resources = list(new_resource_set - old_resource_set)
    for resource_id in new_resources:
        change_list.append({u'type': u'new_resource',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'resource_name':
                            new_resource_dict[resource_id]['name'],
                            u'resource_id': resource_id})

    # get the IDs of resources that have been deleted between versions
    deleted_resources = list(old_resource_set - new_resource_set)
    for resource_id in deleted_resources:
        change_list.append({u'type': u'delete_resource',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'resource_id': resource_id,
                            u'resource_name':
                            old_resource_dict[resource_id]['name'],
                            u'old_activity_id': old_activity_id})

    # now check the resources that are in both and see if any
    # have been changed
    resources = new_resource_set.intersection(old_resource_set)
    for resource_id in resources:
        old_metadata = old_resource_dict[resource_id]
        new_metadata = new_resource_dict[resource_id]

        if old_metadata['name'] != new_metadata['name']:
            change_list.append({u'type': u'resource_name',
                                u'title': new['title'],
                                u'old_pkg_id': old['id'],
                                u'new_pkg_id': new['id'],
                                u'resource_id': resource_id,
                                u'old_resource_name':
                                old_resource_dict[resource_id]['name'],
                                u'new_resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'old_activity_id': old_activity_id})

        # you can't remove a format, but if a resource's format isn't
        # recognized, it won't have one set

        # if a format was not originally set and the user set one
        if not old_metadata['format'] and new_metadata['format']:
            change_list.append({u'type': u'resource_format',
                                u'method': u'add',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'org_id': new['organization']['id']
                                    if new['organization'] else u'',
                                u'format': new_metadata['format']})

        # if both versions have a format but the format changed
        elif old_metadata['format'] != new_metadata['format']:
            change_list.append({u'type': u'resource_format',
                                u'method': u'change',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'org_id': new['organization']['id']
                                    if new['organization'] else u'',
                                u'old_format': old_metadata['format'],
                                u'new_format': new_metadata['format']})

        # if the description changed
        if not old_metadata['description'] and \
                new_metadata['description']:
            change_list.append({u'type': u'resource_desc',
                                u'method': u'add',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'new_desc': new_metadata['description']})

        # if there was a description but the user removed it
        elif old_metadata['description'] and \
                not new_metadata['description']:
            change_list.append({u'type': u'resource_desc',
                                u'method': u'remove',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name']})

        # if both have descriptions but they are different
        elif old_metadata['description'] != new_metadata['description']:
            change_list.append({u'type': u'resource_desc',
                                u'method': u'change',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_resource_dict[resource_id]['name'],
                                u'new_desc': new_metadata['description'],
                                u'old_desc': old_metadata['description']})

        # check if the url changes (e.g. user uploaded a new file)
        # TODO: use regular expressions to determine the actual name of the
        # new and old files
        if old_metadata['url'] != new_metadata['url']:
            change_list.append({u'type': u'new_file',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_metadata['name']})

        # check any extra fields in the resource
        # remove default fields from these sets to make sure we only check
        # for changes to extra fields
        old_fields_set = set(old_metadata.keys())
        old_fields_set = old_fields_set - default_fields_set
        new_fields_set = set(new_metadata.keys())
        new_fields_set = new_fields_set - default_fields_set

        # determine if any new extra fields have been added
        new_fields = list(new_fields_set - old_fields_set)
        if len(new_fields) == 1:
            if new_metadata[new_fields[0]]:
                change_list.append({u'type': u'resource_extras',
                                    u'method': u'add_one_value',
                                    u'pkg_id': new['id'],
                                    u'title': new['title'],
                                    u'resource_id': resource_id,
                                    u'resource_name':
                                    new_metadata['name'],
                                    u'key': new_fields[0],
                                    u'value': new_metadata[new_fields[0]]})
            else:
                change_list.append({u'type': u'resource_extras',
                                    u'method': u'add_one_no_value',
                                    u'pkg_id': new['id'],
                                    u'title': new['title'],
                                    u'resource_id': resource_id,
                                    u'resource_name':
                                    new_metadata['name'],
                                    u'key': new_fields[0]})
        elif len(new_fields) > 1:
            change_list.append({u'type': u'resource_extras',
                                u'method': u'add_multiple',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_metadata['name'],
                                u'key_list': new_fields,
                                u'value_list':
                                [new_metadata[field] for field in new_fields]})

        # determine if any extra fields have been removed
        deleted_fields = list(old_fields_set - new_fields_set)
        if len(deleted_fields) == 1:
            change_list.append({u'type': u'resource_extras',
                                u'method': u'remove_one',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_metadata['name'],
                                u'key': deleted_fields[0]})
        elif len(deleted_fields) > 1:
            change_list.append({u'type': u'resource_extras',
                                u'method': u'remove_multiple',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'resource_id': resource_id,
                                u'resource_name':
                                new_metadata['name'],
                                u'key_list': deleted_fields})

        # determine if any extra fields have been changed
        # changed_fields is only a set of POTENTIALLY changed fields - we
        # still have to check if any of the values associated with the fields
        # have actually changed
        changed_fields = list(new_fields_set.intersection(old_fields_set))
        for field in changed_fields:
            if new_metadata[field] != old_metadata[field]:
                if new_metadata[field] and old_metadata[field]:
                    change_list.append({u'type': u'resource_extras',
                                        u'method': u'change_value_with_old',
                                        u'pkg_id': new['id'],
                                        u'title': new['title'],
                                        u'resource_id': resource_id,
                                        u'resource_name':
                                        new_metadata['name'],
                                        u'key': field,
                                        u'old_value': old_metadata[field],
                                        u'new_value': new_metadata[field]})
                elif not old_metadata[field]:
                    change_list.append({u'type': u'resource_extras',
                                        u'method': u'change_value_no_old',
                                        u'pkg_id': new['id'],
                                        u'title': new['title'],
                                        u'resource_id': resource_id,
                                        u'resource_name':
                                        new_metadata['name'],
                                        u'key': field,
                                        u'new_value': new_metadata[field]})
                elif not new_metadata[field]:
                    change_list.append({u'type': u'resource_extras',
                                        u'method': u'change_value_no_new',
                                        u'pkg_id': new['id'],
                                        u'title': new['title'],
                                        u'resource_id': resource_id,
                                        u'resource_name':
                                        new_metadata['name'],
                                        u'key': field})


def check_metadata_changes(change_list, old, new):
    '''
    Compares two versions of a dataset and records the changes between them
    (excluding resources) in change_list.
    '''
    # if the title has changed
    if old['title'] != new['title']:
        _title_change(change_list, old, new)

    # if the owner organization changed
    if old['owner_org'] != new['owner_org']:
        _org_change(change_list, old, new)

    # if the maintainer of the dataset changed
    if old['maintainer'] != new['maintainer']:
        _maintainer_change(change_list, old, new)

    # if the maintainer email of the dataset changed
    if old['maintainer_email'] != new['maintainer_email']:
        _maintainer_email_change(change_list, old, new)

    # if the author of the dataset changed
    if old['author'] != new['author']:
        _author_change(change_list, old, new)

    # if the author email of the dataset changed
    if old['author_email'] != new['author_email']:
        _author_email_change(change_list, old, new)

    # if the visibility of the dataset changed
    if old['private'] != new['private']:
        change_list.append({u'type': u'private', u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'new':
                            u'Private' if bool(new['private'])
                            else u'Public'})

    # if the description of the dataset changed
    if old['notes'] != new['notes']:
        _notes_change(change_list, old, new)

    # make sets out of the tags for each dataset
    old_tags = {tag['name'] for tag in old['tags']}
    new_tags = {tag['name'] for tag in new['tags']}
    # if the tags have changed
    if old_tags != new_tags:
        _tag_change(change_list, new_tags, old_tags, new)

    # if the license has changed
    if old['license_title'] != new['license_title']:
        _license_change(change_list, old, new)

    # if the name of the dataset has changed
    # this is only visible to the user via the dataset's URL,
    # so display the change using that
    if old['name'] != new['name']:
        _name_change(change_list, old, new)

    # if the source URL (metadata value, not the actual URL of the dataset)
    # has changed
    if old['url'] != new['url']:
        _url_change(change_list, old, new)

    # if the user-provided version has changed
    if old['version'] != new['version']:
        _version_change(change_list, old, new)

    # check whether fields added by extensions or custom fields
    # (in the "extras" field) have been changed

    _extension_fields(change_list, old, new)
    _extra_fields(change_list, old, new)


def _title_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's title between two versions
    (old and new) to change_list.
    '''
    change_list.append({u'type': u'title', u'id': new['name'],
                        u'new_title': new['title'],
                        u'old_title': old['title']})


def _org_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's organization between
    two versions (old and new) to change_list.
    '''

    # if both versions belong to an organization
    if old['owner_org'] and new['owner_org']:
        change_list.append({u'type': u'org',
                            u'method': u'change',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'old_org_id': old['organization']['id'],
                            u'old_org_title':
                            old['organization']['title'],
                            u'new_org_id': new['organization']['id'],
                            u'new_org_title': new['organization']['title']})
    # if the dataset was not in an organization before and it is now
    elif not old['owner_org'] and new['owner_org']:
        change_list.append({u'type': u'org',
                            u'method': u'add',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'new_org_id': new['organization']['id'],
                            u'new_org_title':
                            new['organization']['title']})
    # if the user removed the organization
    else:
        change_list.append({u'type': u'org',
                            u'method': u'remove',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'old_org_id': old['organization']['id'],
                            u'old_org_title':
                            old['organization']['title']})


def _maintainer_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's maintainer field between two
    versions (old and new) to change_list.
    '''
    # if the old dataset had a maintainer
    if old['maintainer'] and new['maintainer']:
        change_list.append({u'type': u'maintainer', u'method': u'change',
                            u'pkg_id': new['id'],
                            u'title': new['title'], u'new_maintainer':
                            new['maintainer'], u'old_maintainer':
                            old['maintainer']})
    # if they removed the maintainer
    elif not new['maintainer']:
        change_list.append({u'type': u'maintainer', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'method': u'remove'})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'maintainer', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'new_maintainer': new['maintainer'],
                            u'method': u'add'})


def _maintainer_email_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's maintainer e-mail address
    field between two versions (old and new) to change_list.
    '''
    # if the old dataset had a maintainer email
    if old['maintainer_email'] and new['maintainer_email']:
        change_list.append({u'type': u'maintainer_email', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'new_maintainer_email': new['maintainer_email'],
                            u'old_maintainer_email':
                            old['maintainer_email'],
                            u'method': u'change'})
    # if they removed the maintainer email
    elif not new['maintainer_email']:
        change_list.append({u'type': u'maintainer_email', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'method': u'remove'})
    # if there wasn't one there before e
    else:
        change_list.append({u'type': u'maintainer_email', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'new_maintainer_email': new['maintainer_email'],
                            u'method': u'add'})


def _author_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's author field between two
    versions (old and new) to change_list.
    '''
    # if the old dataset had an author
    if old['author'] and new['author']:
        change_list.append({u'type': u'author', u'pkg_id': new['id'],
                            u'title': new['title'], u'new_author':
                            new['author'], u'old_author': old['author'],
                            u'method': u'change'})
    # if they removed the author
    elif not new['author']:
        change_list.append({u'type': u'author', u'pkg_id': new['id'],
                            u'title': new['title'], u'method': u'remove'})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'author', u'pkg_id': new['id'],
                            u'title': new['title'], u'new_author':
                            new['author'], u'method': u'add'})


def _author_email_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's author e-mail address field
    between two versions (old and new) to change_list.
    '''
    if old['author_email'] and new['author_email']:
        change_list.append({u'type': u'author_email', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'new_author_email': new['author_email'],
                            u'old_author_email': old['author_email'],
                            u'method': u'change'})
    # if they removed the author
    elif not new['author_email']:
        change_list.append({u'type': u'author_email', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'method': u'remove'})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'author_email', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'new_author_email': new['author_email'],
                            u'method': u'add'})


def _notes_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's description between two
    versions (old and new) to change_list.
    '''
    # if the old dataset had a description
    if old['notes'] and new['notes']:
        change_list.append({u'type': u'notes', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'new_notes': new['notes'],
                            u'old_notes': old['notes'],
                            u'method': u'change'})
    elif not new['notes']:
        change_list.append({u'type': u'notes', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'method': u'remove'})
    else:
        change_list.append({u'type': u'notes', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'new_notes': new['notes'], u'method': u'add'})


def _tag_change(change_list, new_tags, old_tags, new):
    '''
    Appends a summary of a change to a dataset's tag list between two
    versions (old and new) to change_list.
    '''
    deleted_tags = old_tags - new_tags
    deleted_tags_list = list(deleted_tags)
    if len(deleted_tags) == 1:
        change_list.append({u'type': u'tags', u'method': u'remove_one',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'tag': deleted_tags_list[0]})
    elif len(deleted_tags) > 1:
        change_list.append({u'type': u'tags', u'method': u'remove_multiple',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'tags': deleted_tags_list})

    added_tags = new_tags - old_tags
    added_tags_list = list(added_tags)
    if len(added_tags) == 1:
        change_list.append({u'type': u'tags', u'method': u'add_one', u'pkg_id':
                            new['id'], u'title': new['title'],
                            u'tag': added_tags_list[0]})
    elif len(added_tags) > 1:
        change_list.append({u'type': u'tags', u'method': u'add_multiple',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'tags': added_tags_list})


def _license_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's license between two versions
    (old and new) to change_list.
    '''
    old_license_url = u""
    new_license_url = u""
    # if the license has a URL
    if u'license_url' in old and old['license_url']:
        old_license_url = old['license_url']
    if u'license_url' in new and new['license_url']:
        new_license_url = new['license_url']
    change_list.append({u'type': u'license', u'pkg_id': new['id'],
                        u'title': new['title'],
                        u'old_url': old_license_url,
                        u'new_url': new_license_url, u'new_title':
                        new['license_title'], u'old_title':
                        old['license_title']})


def _name_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's name (and thus the URL it
    can be accessed at) between two versions (old and new) to
    change_list.
    '''
    change_list.append({u'type': u'name', u'pkg_id': new['id'],
                        u'title': new['title'], u'old_name':
                        old['name'], u'new_name': new['name']})


def _url_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's source URL (metadata field,
    not its actual URL in the datahub) between two versions (old and
    new) to change_list.
    '''
    # if both old and new versions have source URLs
    if old['url'] and new['url']:
        change_list.append({u'type': u'url', u'method': u'change',
                            u'pkg_id': new['id'], u'title':
                            new['title'], u'new_url': new['url'],
                            u'old_url': old['url']})
    # if the user removed the source URL
    elif not new['url']:
        change_list.append({u'type': u'url', u'method': u'remove',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'old_url': old['url']})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'url', u'method': u'add',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'new_url': new['url']})


def _version_change(change_list, old, new):
    '''
    Appends a summary of a change to a dataset's version field (inputted
    by the user, not from version control) between two versions (old
    and new) to change_list.
    '''
    # if both old and new versions have version numbers
    if old['version'] and new['version']:
        change_list.append({u'type': u'version', u'method': u'change',
                            u'pkg_id': new['id'], u'title':
                            new['title'], u'old_version':
                            old['version'], u'new_version':
                            new['version']})
    # if the user removed the version number
    elif not new['version']:
        change_list.append({u'type': u'version', u'method': u'remove',
                            u'pkg_id': new['id'],
                            u'title': new['title']})
    # if there wasn't one there before
    else:
        change_list.append({u'type': u'version', u'method': u'add',
                            u'pkg_id': new['id'],
                            u'title': new['title'],
                            u'new_version': new['version']})


def _extension_fields(change_list, old, new):
    '''
    Checks whether any fields that have been added to the package
    dictionaries by CKAN extensions have been changed between versions.
    If there have been any changes between the two versions (old and
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
    old_set = set(old.keys())
    new_set = set(new.keys())

    # set of additional fields in the new dictionary
    addl_fields_new = new_set - fields_set
    # set of additional fields in the old dictionary
    addl_fields_old = old_set - fields_set
    # set of additional fields in both
    addl_fields = addl_fields_new.intersection(addl_fields_old)

    # do NOT display a change if any additional fields have been
    # added or deleted, since that is not a change made by the user
    # from the web interface

    # if additional fields have been changed
    addl_fields_list = list(addl_fields)
    for field in addl_fields_list:
        if old[field] != new[field]:
            change_list.append({u'type': u'extension_fields',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'key': field,
                                u'value': new[field]})


def _extra_fields(change_list, old, new):
    '''
    Checks whether a user has added, removed, or changed any extra fields
    from the web interface (or API?) and appends a summary of each change to
    change_list.
    '''
    if u'extras' in new:
        extra_fields_new = _extras_to_dict(new['extras'])
        extra_new_set = set(extra_fields_new.keys())

        # if the old version has extra fields, we need
        # to compare the new version's extras to the old ones
        if u'extras' in old:
            extra_fields_old = _extras_to_dict(old['extras'])
            extra_old_set = set(extra_fields_old.keys())

            # if some fields were added
            new_fields = list(extra_new_set - extra_old_set)
            if len(new_fields) == 1:
                if extra_fields_new[new_fields[0]]:
                    change_list.append({u'type': u'extra_fields',
                                        u'method': u'add_one_value',
                                        u'pkg_id': new['id'],
                                        u'title': new['title'],
                                        u'key': new_fields[0],
                                        u'value':
                                        extra_fields_new[new_fields[0]]})
                else:
                    change_list.append({u'type': u'extra_fields',
                                        u'method': u'add_one_no_value',
                                        u'pkg_id': new['id'],
                                        u'title': new['title'],
                                        u'key': new_fields[0]})
            elif len(new_fields) > 1:
                change_list.append({u'type': u'extra_fields',
                                    u'method': u'add_multiple',
                                    u'pkg_id': new['id'],
                                    u'title': new['title'],
                                    u'key_list': new_fields,
                                    u'value_list': extra_fields_new})

            # if some fields were deleted
            deleted_fields = list(extra_old_set - extra_new_set)
            if len(deleted_fields) == 1:
                change_list.append({u'type': u'extra_fields',
                                    u'method': u'remove_one',
                                    u'pkg_id': new['id'],
                                    u'title': new['title'],
                                    u'key': deleted_fields[0]})
            elif len(deleted_fields) > 1:
                change_list.append({u'type': u'extra_fields',
                                    u'method': u'remove_multiple',
                                    u'pkg_id': new['id'],
                                    u'title': new['title'],
                                    u'key_list': deleted_fields})

            # if some existing fields were changed
            # list of extra fields in both the old and new versions
            extra_fields = list(extra_new_set.intersection(extra_old_set))
            for field in extra_fields:
                if extra_fields_old[field] != extra_fields_new[field]:
                    if extra_fields_old[field]:
                        change_list.append({u'type': u'extra_fields',
                                            u'method':
                                            u'change_with_old_value',
                                            u'pkg_id': new['id'],
                                            u'title': new['title'],
                                            u'key': field,
                                            u'old_value':
                                            extra_fields_old[field],
                                            u'new_value':
                                            extra_fields_new[field]})
                    else:
                        change_list.append({u'type': u'extra_fields',
                                            u'method': u'change_no_old_value',
                                            u'pkg_id': new['id'],
                                            u'title': new['title'],
                                            u'key': field,
                                            u'new_value':
                                            extra_fields_new[field]})

        # if the old version didn't have an extras field,
        # the user could only have added a field (not changed or deleted)
        else:
            new_fields = list(extra_new_set)
            if len(new_fields) == 1:
                if extra_fields_new[new_fields[0]]:
                    change_list.append({u'type': u'extra_fields',
                                        u'method': u'add_one_value',
                                        u'pkg_id': new['id'],
                                        u'title': new['title'],
                                        u'key': new_fields[0],
                                        u'value':
                                        extra_fields_new[new_fields[0]]})
                else:
                    change_list.append({u'type': u'extra_fields',
                                        u'method': u'add_one_no_value',
                                        u'pkg_id': new['id'],
                                        u'title': new['title'],
                                        u'key': new_fields[0]})

            elif len(new_fields) > 1:
                change_list.append({u'type': u'extra_fields',
                                    u'method': u'add_multiple',
                                    u'pkg_id': new['id'],
                                    u'title': new['title'],
                                    u'key_list': new_fields,
                                    u'value_list': extra_fields_new})

    elif u'extras' in old:
        deleted_fields = _extras_to_dict(old['extras']).keys()
        if len(deleted_fields) == 1:
            change_list.append({u'type': u'extra_fields',
                                u'method': u'remove_one',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'key': deleted_fields[0]})
        elif len(deleted_fields) > 1:
            change_list.append({u'type': u'extra_fields',
                                u'method': u'remove_multiple',
                                u'pkg_id': new['id'],
                                u'title': new['title'],
                                u'key_list': deleted_fields})
