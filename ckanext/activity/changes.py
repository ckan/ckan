# encoding: utf-8
"""
Functions for generating a list of differences between two versions of a
dataset
"""
from __future__ import annotations

import logging
from typing import Any
from typing_extensions import TypeAlias, TypedDict

log = logging.getLogger(__name__)

Data: TypeAlias = "dict[str, Any]"
ChangeList: TypeAlias = "list[Data]"


class Extra(TypedDict):
    key: str
    value: Any


def _extras_to_dict(extras_list: list[Extra]) -> Data:
    """
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
    """
    ret_dict = {}
    # the extras_list is a list of dictionaries
    for dict in extras_list:
        ret_dict[dict["key"]] = dict["value"]

    return ret_dict


def check_resource_changes(
    change_list: ChangeList, old: Data, new: Data, old_activity_id: str
) -> None:
    """
    Compares two versions of a dataset and records the changes between them
    (just the resources) in change_list. e.g. resources that are added, changed
    or deleted. For existing resources, checks whether their names, formats,
    and/or descriptions have changed, as well as whether the url changed (e.g.
    a new file has been uploaded for the resource).
    """

    # list of default fields in a resource's metadata dictionary - used
    # later to ensure that we don't count changes to default fields as changes
    # to extra fields
    fields = [
        "package_id",
        "url",
        "revision_id",
        "description",
        "format",
        "hash",
        "name",
        "resource_type",
        "mimetype",
        "mimetype_inner",
        "cache_url",
        "size",
        "created",
        "last_modified",
        "metadata_modified",
        "cache_last_updated",
        "upload",
        "position",
    ]
    default_fields_set = set(fields)

    # make a set of the resource IDs present in old and new
    old_resource_set = set()
    old_resource_dict = {}
    new_resource_set = set()
    new_resource_dict = {}

    for resource in old.get("resources", []):
        old_resource_set.add(resource["id"])
        old_resource_dict[resource["id"]] = {
            key: value for (key, value) in resource.items() if key != "id"
        }

    for resource in new.get("resources", []):
        new_resource_set.add(resource["id"])
        new_resource_dict[resource["id"]] = {
            key: value for (key, value) in resource.items() if key != "id"
        }

    # get the IDs of the resources that have been added between the versions
    new_resources = list(new_resource_set - old_resource_set)
    for resource_id in new_resources:
        change_list.append(
            {
                "type": "new_resource",
                "pkg_id": new["id"],
                "title": new.get("title"),
                "resource_name": new_resource_dict[resource_id].get("name"),
                "resource_id": resource_id,
            }
        )

    # get the IDs of resources that have been deleted between versions
    deleted_resources = list(old_resource_set - new_resource_set)
    for resource_id in deleted_resources:
        change_list.append(
            {
                "type": "delete_resource",
                "pkg_id": new["id"],
                "title": new.get("title"),
                "resource_id": resource_id,
                "resource_name": old_resource_dict[resource_id].get("name"),
                "old_activity_id": old_activity_id,
            }
        )

    # now check the resources that are in both and see if any
    # have been changed
    resources = new_resource_set.intersection(old_resource_set)
    for resource_id in resources:
        old_metadata = old_resource_dict[resource_id]
        new_metadata = new_resource_dict[resource_id]

        if old_metadata.get("name") != new_metadata.get("name"):
            change_list.append(
                {
                    "type": "resource_name",
                    "title": new.get("title"),
                    "old_pkg_id": old["id"],
                    "new_pkg_id": new["id"],
                    "resource_id": resource_id,
                    "old_resource_name": old_resource_dict[resource_id].get(
                        "name"
                    ),
                    "new_resource_name": new_resource_dict[resource_id].get(
                        "name"
                    ),
                    "old_activity_id": old_activity_id,
                }
            )

        # you can't remove a format, but if a resource's format isn't
        # recognized, it won't have one set

        # if a format was not originally set and the user set one
        if not old_metadata.get("format") and new_metadata.get("format"):
            change_list.append(
                {
                    "type": "resource_format",
                    "method": "add",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_resource_dict[resource_id].get(
                        "name"
                    ),
                    "org_id": new["organization"]["id"]
                    if new.get("organization")
                    else "",
                    "format": new_metadata.get("format"),
                }
            )

        # if both versions have a format but the format changed
        elif old_metadata.get("format") != new_metadata.get("format"):
            change_list.append(
                {
                    "type": "resource_format",
                    "method": "change",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_resource_dict[resource_id].get(
                        "name"
                    ),
                    "org_id": new["organization"]["id"]
                    if new.get("organization")
                    else "",
                    "old_format": old_metadata.get("format"),
                    "new_format": new_metadata.get("format"),
                }
            )

        # if the description changed
        if not old_metadata.get("description") and new_metadata.get(
            "description"
        ):
            change_list.append(
                {
                    "type": "resource_desc",
                    "method": "add",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_resource_dict[resource_id].get(
                        "name"
                    ),
                    "new_desc": new_metadata.get("description"),
                }
            )

        # if there was a description but the user removed it
        elif old_metadata.get("description") and not new_metadata.get(
            "description"
        ):
            change_list.append(
                {
                    "type": "resource_desc",
                    "method": "remove",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_resource_dict[resource_id].get(
                        "name"
                    ),
                }
            )

        # if both have descriptions but they are different
        elif old_metadata.get("description") != new_metadata.get(
            "description"
        ):
            change_list.append(
                {
                    "type": "resource_desc",
                    "method": "change",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_resource_dict[resource_id].get(
                        "name"
                    ),
                    "new_desc": new_metadata.get("description"),
                    "old_desc": old_metadata.get("description"),
                }
            )

        # check if the url changes (e.g. user uploaded a new file)
        # TODO: use regular expressions to determine the actual name of the
        # new and old files
        if old_metadata.get("url") != new_metadata.get("url"):
            change_list.append(
                {
                    "type": "new_file",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_metadata.get("name"),
                }
            )

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
                change_list.append(
                    {
                        "type": "resource_extras",
                        "method": "add_one_value",
                        "pkg_id": new["id"],
                        "title": new.get("title"),
                        "resource_id": resource_id,
                        "resource_name": new_metadata.get("name"),
                        "key": new_fields[0],
                        "value": new_metadata[new_fields[0]],
                    }
                )
            else:
                change_list.append(
                    {
                        "type": "resource_extras",
                        "method": "add_one_no_value",
                        "pkg_id": new["id"],
                        "title": new.get("title"),
                        "resource_id": resource_id,
                        "resource_name": new_metadata.get("name"),
                        "key": new_fields[0],
                    }
                )
        elif len(new_fields) > 1:
            change_list.append(
                {
                    "type": "resource_extras",
                    "method": "add_multiple",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_metadata.get("name"),
                    "key_list": new_fields,
                    "value_list": [
                        new_metadata[field] for field in new_fields
                    ],
                }
            )

        # determine if any extra fields have been removed
        deleted_fields = list(old_fields_set - new_fields_set)
        if len(deleted_fields) == 1:
            change_list.append(
                {
                    "type": "resource_extras",
                    "method": "remove_one",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_metadata.get("name"),
                    "key": deleted_fields[0],
                }
            )
        elif len(deleted_fields) > 1:
            change_list.append(
                {
                    "type": "resource_extras",
                    "method": "remove_multiple",
                    "pkg_id": new["id"],
                    "title": new.get("title"),
                    "resource_id": resource_id,
                    "resource_name": new_metadata.get("name"),
                    "key_list": deleted_fields,
                }
            )

        # determine if any extra fields have been changed
        # changed_fields is only a set of POTENTIALLY changed fields - we
        # still have to check if any of the values associated with the fields
        # have actually changed
        changed_fields = list(new_fields_set.intersection(old_fields_set))
        for field in changed_fields:
            if new_metadata[field] != old_metadata[field]:
                if new_metadata[field] and old_metadata[field]:
                    change_list.append(
                        {
                            "type": "resource_extras",
                            "method": "change_value_with_old",
                            "pkg_id": new["id"],
                            "title": new.get("title"),
                            "resource_id": resource_id,
                            "resource_name": new_metadata.get("name"),
                            "key": field,
                            "old_value": old_metadata[field],
                            "new_value": new_metadata[field],
                        }
                    )
                elif not old_metadata[field]:
                    change_list.append(
                        {
                            "type": "resource_extras",
                            "method": "change_value_no_old",
                            "pkg_id": new["id"],
                            "title": new.get("title"),
                            "resource_id": resource_id,
                            "resource_name": new_metadata.get("name"),
                            "key": field,
                            "new_value": new_metadata[field],
                        }
                    )
                elif not new_metadata[field]:
                    change_list.append(
                        {
                            "type": "resource_extras",
                            "method": "change_value_no_new",
                            "pkg_id": new["id"],
                            "title": new.get("title"),
                            "resource_id": resource_id,
                            "resource_name": new_metadata.get("name"),
                            "key": field,
                        }
                    )


def check_metadata_changes(
    change_list: ChangeList, old: Data, new: Data
) -> None:
    """
    Compares two versions of a dataset and records the changes between them
    (excluding resources) in change_list.
    """
    # if the title has changed
    if old.get("title") != new.get("title"):
        _title_change(change_list, old, new)

    # if the owner organization changed
    if old.get("owner_org") != new.get("owner_org"):
        _org_change(change_list, old, new)

    # if the maintainer of the dataset changed
    if old.get("maintainer") != new.get("maintainer"):
        _maintainer_change(change_list, old, new)

    # if the maintainer email of the dataset changed
    if old.get("maintainer_email") != new.get("maintainer_email"):
        _maintainer_email_change(change_list, old, new)

    # if the author of the dataset changed
    if old.get("author") != new.get("author"):
        _author_change(change_list, old, new)

    # if the author email of the dataset changed
    if old.get("author_email") != new.get("author_email"):
        _author_email_change(change_list, old, new)

    # if the visibility of the dataset changed
    if old.get("private") != new.get("private"):
        change_list.append(
            {
                "type": "private",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new": "Private" if bool(new.get("private")) else "Public",
            }
        )

    # if the description of the dataset changed
    if old.get("notes") != new.get("notes"):
        _notes_change(change_list, old, new)

    # make sets out of the tags for each dataset
    old_tags = {tag.get("name") for tag in old.get("tags", [])}
    new_tags = {tag.get("name") for tag in new.get("tags", [])}
    # if the tags have changed
    if old_tags != new_tags:
        _tag_change(change_list, new_tags, old_tags, new)

    # if the license has changed
    if old.get("license_title") != new.get("license_title"):
        _license_change(change_list, old, new)

    # if the name of the dataset has changed
    # this is only visible to the user via the dataset's URL,
    # so display the change using that
    if old.get("name") != new.get("name"):
        _name_change(change_list, old, new)

    # if the source URL (metadata value, not the actual URL of the dataset)
    # has changed
    if old.get("url") != new.get("url"):
        _url_change(change_list, old, new)

    # if the user-provided version has changed
    if old.get("version") != new.get("version"):
        _version_change(change_list, old, new)

    # check whether fields added by extensions or custom fields
    # (in the "extras" field) have been changed

    _extension_fields(change_list, old, new)
    _extra_fields(change_list, old, new)


def check_metadata_org_changes(change_list: ChangeList, old: Data, new: Data):
    """
    Compares two versions of a organization and records the changes between
    them in change_list.
    """
    # if the title has changed
    if old.get("title") != new.get("title"):
        _title_change(change_list, old, new)

    # if the description of the organization changed
    if old.get("description") != new.get("description"):
        _description_change(change_list, old, new)

    # if the image URL has changed
    if old.get("image_url") != new.get("image_url"):
        _image_url_change(change_list, old, new)


def _title_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's title between two versions
    (old and new) to change_list.
    """
    change_list.append(
        {
            "type": "title",
            "id": new.get("name"),
            "new_title": new.get("title"),
            "old_title": old.get("title"),
        }
    )


def _org_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's organization between
    two versions (old and new) to change_list.
    """

    # if both versions belong to an organization
    if old.get("owner_org") and new.get("owner_org"):
        change_list.append(
            {
                "type": "org",
                "method": "change",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "old_org_id": old["organization"].get("id"),
                "old_org_title": old["organization"].get("title"),
                "new_org_id": new["organization"].get("id"),
                "new_org_title": new["organization"].get("title"),
            }
        )
    # if the dataset was not in an organization before and it is now
    elif not old.get("owner_org") and new.get("owner_org"):
        change_list.append(
            {
                "type": "org",
                "method": "add",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_org_id": new["organization"].get("id"),
                "new_org_title": new["organization"].get("title"),
            }
        )
    # if the user removed the organization
    else:
        change_list.append(
            {
                "type": "org",
                "method": "remove",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "old_org_id": old["organization"].get("id"),
                "old_org_title": old["organization"].get("title"),
            }
        )


def _maintainer_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's maintainer field between two
    versions (old and new) to change_list.
    """
    # if the old dataset had a maintainer
    if old.get("maintainer") and new.get("maintainer"):
        change_list.append(
            {
                "type": "maintainer",
                "method": "change",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_maintainer": new["maintainer"],
                "old_maintainer": old["maintainer"],
            }
        )
    # if they removed the maintainer
    elif not new.get("maintainer"):
        change_list.append(
            {
                "type": "maintainer",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "method": "remove",
            }
        )
    # if there wasn't one there before
    else:
        change_list.append(
            {
                "type": "maintainer",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_maintainer": new.get("maintainer"),
                "method": "add",
            }
        )


def _maintainer_email_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's maintainer e-mail address
    field between two versions (old and new) to change_list.
    """
    # if the old dataset had a maintainer email
    if old.get("maintainer_email") and new.get("maintainer_email"):
        change_list.append(
            {
                "type": "maintainer_email",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_maintainer_email": new.get("maintainer_email"),
                "old_maintainer_email": old.get("maintainer_email"),
                "method": "change",
            }
        )
    # if they removed the maintainer email
    elif not new.get("maintainer_email"):
        change_list.append(
            {
                "type": "maintainer_email",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "method": "remove",
            }
        )
    # if there wasn't one there before e
    else:
        change_list.append(
            {
                "type": "maintainer_email",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_maintainer_email": new.get("maintainer_email"),
                "method": "add",
            }
        )


def _author_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's author field between two
    versions (old and new) to change_list.
    """
    # if the old dataset had an author
    if old.get("author") and new.get("author"):
        change_list.append(
            {
                "type": "author",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_author": new.get("author"),
                "old_author": old.get("author"),
                "method": "change",
            }
        )
    # if they removed the author
    elif not new.get("author"):
        change_list.append(
            {
                "type": "author",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "method": "remove",
            }
        )
    # if there wasn't one there before
    else:
        change_list.append(
            {
                "type": "author",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_author": new.get("author"),
                "method": "add",
            }
        )


def _author_email_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's author e-mail address field
    between two versions (old and new) to change_list.
    """
    if old.get("author_email") and new.get("author_email"):
        change_list.append(
            {
                "type": "author_email",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_author_email": new.get("author_email"),
                "old_author_email": old.get("author_email"),
                "method": "change",
            }
        )
    # if they removed the author
    elif not new.get("author_email"):
        change_list.append(
            {
                "type": "author_email",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "method": "remove",
            }
        )
    # if there wasn't one there before
    else:
        change_list.append(
            {
                "type": "author_email",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_author_email": new.get("author_email"),
                "method": "add",
            }
        )


def _notes_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's description between two
    versions (old and new) to change_list.
    """
    # if the old dataset had a description
    if old.get("notes") and new.get("notes"):
        change_list.append(
            {
                "type": "notes",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_notes": new.get("notes"),
                "old_notes": old.get("notes"),
                "method": "change",
            }
        )
    elif not new.get("notes"):
        change_list.append(
            {
                "type": "notes",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "method": "remove",
            }
        )
    else:
        change_list.append(
            {
                "type": "notes",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_notes": new.get("notes"),
                "method": "add",
            }
        )


def _tag_change(
    change_list: ChangeList, new_tags: set[Any], old_tags: set[Any], new: Data
):
    """
    Appends a summary of a change to a dataset's tag list between two
    versions (old and new) to change_list.
    """
    deleted_tags = old_tags - new_tags
    deleted_tags_list = list(deleted_tags)
    if len(deleted_tags) == 1:
        change_list.append(
            {
                "type": "tags",
                "method": "remove_one",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "tag": deleted_tags_list[0],
            }
        )
    elif len(deleted_tags) > 1:
        change_list.append(
            {
                "type": "tags",
                "method": "remove_multiple",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "tags": deleted_tags_list,
            }
        )

    added_tags = new_tags - old_tags
    added_tags_list = list(added_tags)
    if len(added_tags) == 1:
        change_list.append(
            {
                "type": "tags",
                "method": "add_one",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "tag": added_tags_list[0],
            }
        )
    elif len(added_tags) > 1:
        change_list.append(
            {
                "type": "tags",
                "method": "add_multiple",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "tags": added_tags_list,
            }
        )


def _license_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's license between two versions
    (old and new) to change_list.
    """
    old_license_url = ""
    new_license_url = ""
    # if the license has a URL
    if "license_url" in old and old["license_url"]:
        old_license_url = old["license_url"]
    if "license_url" in new and new["license_url"]:
        new_license_url = new["license_url"]
    change_list.append(
        {
            "type": "license",
            "pkg_id": new.get("id"),
            "title": new.get("title"),
            "old_url": old_license_url,
            "new_url": new_license_url,
            "new_title": new.get("license_title"),
            "old_title": old.get("license_title"),
        }
    )


def _name_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's name (and thus the URL it
    can be accessed at) between two versions (old and new) to
    change_list.
    """
    change_list.append(
        {
            "type": "name",
            "pkg_id": new.get("id"),
            "title": new.get("title"),
            "old_name": old.get("name"),
            "new_name": new.get("name"),
        }
    )


def _url_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's source URL (metadata field,
    not its actual URL in the datahub) between two versions (old and
    new) to change_list.
    """
    # if both old and new versions have source URLs
    if old.get("url") and new.get("url"):
        change_list.append(
            {
                "type": "url",
                "method": "change",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_url": new.get("url"),
                "old_url": old.get("url"),
            }
        )
    # if the user removed the source URL
    elif not new.get("url"):
        change_list.append(
            {
                "type": "url",
                "method": "remove",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "old_url": old.get("url"),
            }
        )
    # if there wasn't one there before
    else:
        change_list.append(
            {
                "type": "url",
                "method": "add",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_url": new.get("url"),
            }
        )


def _version_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a dataset's version field (inputted
    by the user, not from version control) between two versions (old
    and new) to change_list.
    """
    # if both old and new versions have version numbers
    if old.get("version") and new.get("version"):
        change_list.append(
            {
                "type": "version",
                "method": "change",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "old_version": old.get("version"),
                "new_version": new.get("version"),
            }
        )
    # if the user removed the version number
    elif not new.get("version"):
        change_list.append(
            {
                "type": "version",
                "method": "remove",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "old_version": old.get("version"),
            }
        )
    # if there wasn't one there before
    else:
        change_list.append(
            {
                "type": "version",
                "method": "add",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_version": new.get("version"),
            }
        )


def _extension_fields(change_list: ChangeList, old: Data, new: Data):
    """
    Checks whether any fields that have been added to the package
    dictionaries by CKAN extensions have been changed between versions.
    If there have been any changes between the two versions (old and
    new), a general summary of the change is appended to change_list. This
    function does not produce summaries for fields added or deleted by
    extensions, since these changes are not triggered by the user in the web
    interface or API.
    """
    # list of the default metadata fields for a dataset
    # any fields that are not part of this list are custom fields added by a
    # user or extension
    fields = [
        "owner_org",
        "maintainer",
        "maintainer_email",
        "relationships_as_object",
        "private",
        "num_tags",
        "id",
        "metadata_created",
        "metadata_modified",
        "author",
        "author_email",
        "state",
        "version",
        "license_id",
        "type",
        "resources",
        "num_resources",
        "tags",
        "title",
        "groups",
        "creator_user_id",
        "relationships_as_subject",
        "name",
        "isopen",
        "url",
        "notes",
        "license_title",
        "extras",
        "license_url",
        "organization",
        "revision_id",
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
        if old.get(field) != new.get(field):
            change_list.append(
                {
                    "type": "extension_fields",
                    "pkg_id": new.get("id"),
                    "title": new.get("title"),
                    "key": field,
                    "value": new.get(field),
                }
            )


def _extra_fields(change_list: ChangeList, old: Data, new: Data):
    """
    Checks whether a user has added, removed, or changed any extra fields
    from the web interface (or API?) and appends a summary of each change to
    change_list.
    """
    if "extras" in new:
        extra_fields_new = _extras_to_dict(new.get("extras", []))
        extra_new_set = set(extra_fields_new.keys())

        # if the old version has extra fields, we need
        # to compare the new version's extras to the old ones
        if "extras" in old:
            extra_fields_old = _extras_to_dict(old.get("extras", []))
            extra_old_set = set(extra_fields_old.keys())

            # if some fields were added
            new_fields = list(extra_new_set - extra_old_set)
            if len(new_fields) == 1:
                if extra_fields_new[new_fields[0]]:
                    change_list.append(
                        {
                            "type": "extra_fields",
                            "method": "add_one_value",
                            "pkg_id": new.get("id"),
                            "title": new.get("title"),
                            "key": new_fields[0],
                            "value": extra_fields_new[new_fields[0]],
                        }
                    )
                else:
                    change_list.append(
                        {
                            "type": "extra_fields",
                            "method": "add_one_no_value",
                            "pkg_id": new.get("id"),
                            "title": new.get("title"),
                            "key": new_fields[0],
                        }
                    )
            elif len(new_fields) > 1:
                change_list.append(
                    {
                        "type": "extra_fields",
                        "method": "add_multiple",
                        "pkg_id": new.get("id"),
                        "title": new.get("title"),
                        "key_list": new_fields,
                        "value_list": extra_fields_new,
                    }
                )

            # if some fields were deleted
            deleted_fields = list(extra_old_set - extra_new_set)
            if len(deleted_fields) == 1:
                change_list.append(
                    {
                        "type": "extra_fields",
                        "method": "remove_one",
                        "pkg_id": new.get("id"),
                        "title": new.get("title"),
                        "key": deleted_fields[0],
                    }
                )
            elif len(deleted_fields) > 1:
                change_list.append(
                    {
                        "type": "extra_fields",
                        "method": "remove_multiple",
                        "pkg_id": new.get("id"),
                        "title": new.get("title"),
                        "key_list": deleted_fields,
                    }
                )

            # if some existing fields were changed
            # list of extra fields in both the old and new versions
            extra_fields = list(extra_new_set.intersection(extra_old_set))
            for field in extra_fields:
                if extra_fields_old[field] != extra_fields_new[field]:
                    if extra_fields_old[field]:
                        change_list.append(
                            {
                                "type": "extra_fields",
                                "method": "change_with_old_value",
                                "pkg_id": new.get("id"),
                                "title": new.get("title"),
                                "key": field,
                                "old_value": extra_fields_old[field],
                                "new_value": extra_fields_new[field],
                            }
                        )
                    else:
                        change_list.append(
                            {
                                "type": "extra_fields",
                                "method": "change_no_old_value",
                                "pkg_id": new.get("id"),
                                "title": new.get("title"),
                                "key": field,
                                "new_value": extra_fields_new[field],
                            }
                        )

        # if the old version didn't have an extras field,
        # the user could only have added a field (not changed or deleted)
        else:
            new_fields = list(extra_new_set)
            if len(new_fields) == 1:
                if extra_fields_new[new_fields[0]]:
                    change_list.append(
                        {
                            "type": "extra_fields",
                            "method": "add_one_value",
                            "pkg_id": new.get("id"),
                            "title": new.get("title"),
                            "key": new_fields[0],
                            "value": extra_fields_new[new_fields[0]],
                        }
                    )
                else:
                    change_list.append(
                        {
                            "type": "extra_fields",
                            "method": "add_one_no_value",
                            "pkg_id": new.get("id"),
                            "title": new.get("title"),
                            "key": new_fields[0],
                        }
                    )

            elif len(new_fields) > 1:
                change_list.append(
                    {
                        "type": "extra_fields",
                        "method": "add_multiple",
                        "pkg_id": new.get("id"),
                        "title": new.get("title"),
                        "key_list": new_fields,
                        "value_list": extra_fields_new,
                    }
                )

    elif "extras" in old:
        deleted_fields = list(_extras_to_dict(old["extras"]).keys())
        if len(deleted_fields) == 1:
            change_list.append(
                {
                    "type": "extra_fields",
                    "method": "remove_one",
                    "pkg_id": new.get("id"),
                    "title": new.get("title"),
                    "key": deleted_fields[0],
                }
            )
        elif len(deleted_fields) > 1:
            change_list.append(
                {
                    "type": "extra_fields",
                    "method": "remove_multiple",
                    "pkg_id": new.get("id"),
                    "title": new.get("title"),
                    "key_list": deleted_fields,
                }
            )


def _description_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a organization's description between two
    versions (old and new) to change_list.
    """

    # if the old organization had a description
    if old.get("description") and new.get("description"):
        change_list.append(
            {
                "type": "description",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_description": new.get("description"),
                "old_description": old.get("description"),
                "method": "change",
            }
        )
    elif not new.get("description"):
        change_list.append(
            {
                "type": "description",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "method": "remove",
            }
        )
    else:
        change_list.append(
            {
                "type": "description",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_description": new.get("description"),
                "method": "add",
            }
        )


def _image_url_change(change_list: ChangeList, old: Data, new: Data):
    """
    Appends a summary of a change to a organization's image URL between two
    versions (old and new) to change_list.
    """
    # if both old and new versions have image  URLs
    if old.get("image_url") and new.get("image_url"):
        change_list.append(
            {
                "type": "image_url",
                "method": "change",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_image_url": new.get("image_url"),
                "old_image_url": old.get("image_url"),
            }
        )
    # if the user removed the image URL
    elif not new.get("image_url"):
        change_list.append(
            {
                "type": "image_url",
                "method": "remove",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "old_image_url": old.get("image_url"),
            }
        )
    # if there wasn't one there before
    else:
        change_list.append(
            {
                "type": "image_url",
                "method": "add",
                "pkg_id": new.get("id"),
                "title": new.get("title"),
                "new_image_url": new.get("image_url"),
            }
        )
