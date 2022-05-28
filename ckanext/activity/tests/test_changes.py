# encoding: utf-8

import copy

import pytest
from ckanext.activity.changes import (
    check_metadata_changes,
    check_resource_changes,
)
from ckan.tests import helpers
from ckan.tests.factories import Dataset, Organization


@pytest.mark.usefixtures("non_clean_db")
class TestChanges(object):
    def test_title(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch", id=original["id"], title="New title"
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "title"
        assert changes[0]["old_title"] == original["title"]
        assert changes[0]["new_title"] == new["title"]

    def test_name(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch", id=original["id"], name="new-name"
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "name"
        assert changes[0]["old_name"] == original["name"]
        assert changes[0]["new_name"] == "new-name"

    def test_add_extra(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            extras=[{"key": "subject", "value": "science"}],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "extra_fields"
        assert changes[0]["method"] == "add_one_value"
        assert changes[0]["key"] == "subject"
        assert changes[0]["value"] == "science"

    # TODO how to test 'add_one_no_value'?

    def test_add_multiple_extras(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            extras=[
                {"key": "subject", "value": "science"},
                {"key": "topic", "value": "wind"},
            ],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "extra_fields"
        assert changes[0]["method"] == "add_multiple"
        assert set(changes[0]["key_list"]) == set(["subject", "topic"])

    def test_change_extra(self):
        changes = []
        original = Dataset(
            extras=[
                {"key": "subject", "value": "science"},
                {"key": "topic", "value": "wind"},
            ]
        )
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            extras=[
                {"key": "subject", "value": "scientific"},
                {"key": "topic", "value": "wind"},
            ],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "extra_fields"
        assert changes[0]["method"] == "change_with_old_value"
        assert changes[0]["key"] == "subject"
        assert changes[0]["old_value"] == "science"
        assert changes[0]["new_value"] == "scientific"

    def test_change_multiple_extras(self):
        changes = []
        original = Dataset(
            extras=[
                {"key": "subject", "value": "science"},
                {"key": "topic", "value": "wind"},
            ]
        )
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            extras=[
                {"key": "subject", "value": "scientific"},
                {"key": "topic", "value": "rain"},
            ],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 2, changes
        for change in changes:
            assert change["type"] == "extra_fields"
            assert change["method"] == "change_with_old_value"
            if change["key"] == "subject":
                assert change["new_value"] == "scientific"
            else:
                assert change["key"] == "topic"
                assert change["new_value"] == "rain"

    # TODO how to test change2?

    def test_delete_extra(self):
        changes = []
        original = Dataset(
            extras=[
                {"key": "subject", "value": "science"},
                {"key": "topic", "value": "wind"},
            ]
        )
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            extras=[{"key": "topic", "value": "wind"}],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "extra_fields"
        assert changes[0]["method"] == "remove_one"
        assert changes[0]["key"] == "subject"

    def test_delete_multiple_extras(self):
        changes = []
        original = Dataset(
            extras=[
                {"key": "subject", "value": "science"},
                {"key": "topic", "value": "wind"},
                {"key": "geography", "value": "global"},
            ]
        )
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            extras=[{"key": "topic", "value": "wind"}],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "extra_fields"
        assert changes[0]["method"] == "remove_multiple"
        assert set(changes[0]["key_list"]) == set(("subject", "geography"))

    def test_add_maintainer(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch", id=original["id"], maintainer="new maintainer"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_maintainer"] == "new maintainer"

    def test_change_maintainer(self):
        changes = []
        original = Dataset(maintainer="first maintainer")
        new = helpers.call_action(
            "package_patch", id=original["id"], maintainer="new maintainer"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer"
        assert changes[0]["method"] == "change"
        assert changes[0]["old_maintainer"] == "first maintainer"
        assert changes[0]["new_maintainer"] == "new maintainer"

    def test_remove_maintainer(self):
        changes = []
        original = Dataset(maintainer="first maintainer")
        new = helpers.call_action(
            "package_patch", id=original["id"], maintainer=""
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer"
        assert changes[0]["method"] == "remove"

    def test_add_notes(self):
        changes = []
        original = Dataset(notes="")
        new = helpers.call_action(
            "package_patch", id=original["id"], notes="new notes"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "notes"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_notes"] == "new notes"

    def test_change_notes(self):
        changes = []
        original = Dataset(notes="first notes")
        new = helpers.call_action(
            "package_patch", id=original["id"], notes="new notes"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "notes"
        assert changes[0]["method"] == "change"
        assert changes[0]["old_notes"] == "first notes"
        assert changes[0]["new_notes"] == "new notes"

    def test_remove_notes(self):
        changes = []
        original = Dataset(notes="first notes")
        new = helpers.call_action("package_patch", id=original["id"], notes="")

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "notes"
        assert changes[0]["method"] == "remove"

    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", True)
    @pytest.mark.usefixtures("with_request_context")
    def test_add_org(self):
        changes = []
        original = Dataset(owner_org=None)
        new_org = Organization()
        new = helpers.call_action(
            "package_patch", id=original["id"], owner_org=new_org["id"]
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "org"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_org_id"] == new_org["id"]

    @pytest.mark.usefixtures("with_request_context")
    def test_change_org(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org["id"])
        new_org = Organization()
        new = helpers.call_action(
            "package_patch", id=original["id"], owner_org=new_org["id"]
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "org"
        assert changes[0]["method"] == "change"
        assert changes[0]["old_org_id"] == original["organization"]["id"]
        assert changes[0]["new_org_id"] == new_org["id"]

    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", True)
    @pytest.mark.usefixtures("with_request_context")
    def test_remove_org(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org["id"])

        import ckan.model as model

        pkg = model.Package.get(original["id"])
        pkg.owner_org = None
        pkg.save()

        new = helpers.call_action("package_show", id=original["id"])

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "org"
        assert changes[0]["method"] == "remove"

    @pytest.mark.usefixtures("with_request_context")
    def test_make_private(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org["id"], private=False)
        new = helpers.call_action(
            "package_patch", id=original["id"], private=True
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "private"
        assert changes[0]["new"] == "Private"

    @pytest.mark.usefixtures("with_request_context")
    def test_make_public(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org["id"], private=True)
        new = helpers.call_action(
            "package_patch", id=original["id"], private=False
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "private"
        assert changes[0]["new"] == "Public"

    def test_add_tag(self):
        changes = []
        original = Dataset(tags=[{"name": "rivers"}])
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            tags=[{"name": "rivers"}, {"name": "oceans"}],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "tags"
        assert changes[0]["method"] == "add_one"
        assert changes[0]["tag"] == "oceans"

    def test_add_multiple_tags(self):
        changes = []
        original = Dataset(tags=[{"name": "rivers"}])
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            tags=[
                {"name": "rivers"},
                {"name": "oceans"},
                {"name": "streams"},
            ],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "tags"
        assert changes[0]["method"] == "add_multiple"
        assert set(changes[0]["tags"]) == set(("oceans", "streams"))

    def test_delete_tag(self):
        changes = []
        original = Dataset(tags=[{"name": "rivers"}, {"name": "oceans"}])
        new = helpers.call_action(
            "package_patch", id=original["id"], tags=[{"name": "rivers"}]
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "tags"
        assert changes[0]["method"] == "remove_one"
        assert changes[0]["tag"] == "oceans"

    def test_remove_multiple_tags(self):
        changes = []
        original = Dataset(
            tags=[
                {"name": "rivers"},
                {"name": "oceans"},
                {"name": "streams"},
            ]
        )
        new = helpers.call_action(
            "package_patch", id=original["id"], tags=[{"name": "rivers"}]
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "tags"
        assert changes[0]["method"] == "remove_multiple"
        assert set(changes[0]["tags"]) == set(("oceans", "streams"))

    def test_add_url(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch", id=original["id"], url="new url"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "url"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_url"] == "new url"

    def test_change_url(self):
        changes = []
        original = Dataset(url="first url")
        new = helpers.call_action(
            "package_patch", id=original["id"], url="new url"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "url"
        assert changes[0]["method"] == "change"
        assert changes[0]["old_url"] == "first url"
        assert changes[0]["new_url"] == "new url"

    def test_remove_url(self):
        changes = []
        original = Dataset(url="first url")
        new = helpers.call_action("package_patch", id=original["id"], url="")

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "url"
        assert changes[0]["method"] == "remove"

    def test_add_version(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch", id=original["id"], version="new version"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "version"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_version"] == "new version"

    def test_change_version(self):
        changes = []
        original = Dataset(version="first version")
        new = helpers.call_action(
            "package_patch", id=original["id"], version="new version"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "version"
        assert changes[0]["method"] == "change"
        assert changes[0]["old_version"] == "first version"
        assert changes[0]["new_version"] == "new version"

    def test_remove_version(self):
        changes = []
        original = Dataset(version="first version")
        new = helpers.call_action(
            "package_patch", id=original["id"], version=""
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "version"
        assert changes[0]["method"] == "remove"

    def test_add_resource(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                }
            ],
        )

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "new_resource"
        assert changes[0]["resource_name"] == "Image 1"

    def test_add_multiple_resources(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            "package_patch",
            id=original["id"],
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://example.com/image2.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ],
        )

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 2, changes
        assert changes[0]["type"] == "new_resource"
        assert changes[1]["type"] == "new_resource"
        if changes[0]["resource_name"] == "Image 1":
            assert changes[1]["resource_name"] == "Image 2"
        else:
            assert changes[1]["resource_name"] == "Image 1"
            assert changes[0]["resource_name"] == "Image 2"

    def test_change_resource_url(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][1]["url"] = "http://example.com/image_changed.png"
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "new_file"
        assert changes[0]["resource_name"] == "Image 2"

    def test_change_resource_format(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][1]["format"] = "jpg"
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "resource_format"
        assert changes[0]["resource_name"] == "Image 2"

    def test_change_resource_name(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][1]["name"] = "Image changed"
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "resource_name"
        assert changes[0]["old_resource_name"] == "Image 2"
        assert changes[0]["new_resource_name"] == "Image changed"

    def test_change_resource_description(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                    "description": "First image",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 2",
                    "description": "Second image",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][1]["description"] = "changed"
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "resource_desc"
        assert changes[0]["method"] == "change"
        assert changes[0]["resource_name"] == "Image 2"

    def test_add_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                }
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][0]["new key"] = "new value"
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "resource_extras"
        assert changes[0]["method"] == "add_one_value"
        assert changes[0]["key"] == "new key"
        assert changes[0]["value"] == "new value"

    def test_change_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                    "key1": "value1",
                }
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][0]["key1"] = "new value"
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "resource_extras"
        assert changes[0]["method"] == "change_value_with_old"
        assert changes[0]["key"] == "key1"
        assert changes[0]["old_value"] == "value1"
        assert changes[0]["new_value"] == "new value"

    def test_remove_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                    "key1": "value1",
                }
            ]
        )
        new = copy.deepcopy(original)
        del new["resources"][0]["key1"]
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "resource_extras"
        assert changes[0]["method"] == "remove_one"
        assert changes[0]["key"] == "key1"

    def test_change_multiple_resources(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 2",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 3",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][0]["name"] = "changed-1"
        new["resources"][1]["name"] = "changed-2"
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 2, changes
        assert changes[0]["type"] == "resource_name"
        assert changes[1]["type"] == "resource_name"
        if changes[0]["old_resource_name"] == "Image 1":
            assert changes[0]["new_resource_name"] == "changed-1"
        else:
            assert changes[0]["old_resource_name"] == "Image 2"
            assert changes[0]["new_resource_name"] == "changed-2"

    def test_delete_resource(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ]
        )
        new = copy.deepcopy(original)
        del new["resources"][0]
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "delete_resource"
        assert changes[0]["resource_name"] == "Image 1"

    def test_delete_multiple_resources(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 2",
                },
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 3",
                },
            ]
        )
        new = copy.deepcopy(original)
        del new["resources"][1]
        del new["resources"][0]
        new = helpers.call_action("package_update", **new)

        check_resource_changes(changes, original, new, "fake")

        assert len(changes) == 2, changes
        assert changes[0]["type"] == "delete_resource"
        if changes[0]["resource_name"] == "Image 1":
            assert changes[1]["resource_name"] == "Image 2"
        else:
            assert changes[0]["resource_name"] == "Image 2"
            assert changes[1]["resource_name"] == "Image 1"


class TestChangesWithSingleAttributes(object):
    def test_title_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"title": "new title"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "title"
        assert changes[0]["old_title"] is None
        assert changes[0]["new_title"] == "new title"

    def test_title_changed(self):
        changes = []
        original = {"title": "old title"}
        new = {"title": "new title"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "title"
        assert changes[0]["old_title"] == "old title"
        assert changes[0]["new_title"] == "new title"

    def test_title_removed_with_non_existing(self):
        changes = []
        original = {"title": "old title"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "title"
        assert changes[0]["old_title"] == "old title"
        assert changes[0]["new_title"] is None

    def test_owner_org_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new_org = {"id": "new_org_id"}
        new = {"owner_org": new_org["id"], "organization": new_org}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "org"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_org_id"] == new_org["id"]

    def test_owner_org_changed(self):
        changes = []
        old_org = {"id": "old_org_id"}
        original = {"owner_org": old_org["id"], "organization": old_org}
        new_org = {"id": "new_org_id"}
        new = {"owner_org": new_org["id"], "organization": new_org}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "org"
        assert changes[0]["method"] == "change"
        assert changes[0]["old_org_id"] == old_org["id"]
        assert changes[0]["new_org_id"] == new_org["id"]

    def test_owner_org_removed_with_non_existing(self):
        changes = []
        old_org = {"id": "org_id"}
        original = {"owner_org": old_org["id"], "organization": old_org}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "org"
        assert changes[0]["method"] == "remove"
        assert changes[0]["old_org_id"] == old_org["id"]

    def test_maintainer_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"maintainer": "new maintainer"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_maintainer"] == "new maintainer"

    def test_maintainer_changed(self):
        changes = []
        original = {"maintainer": "old maintainer"}
        new = {"maintainer": "new maintainer"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer"
        assert changes[0]["method"] == "change"
        assert changes[0]["new_maintainer"] == "new maintainer"
        assert changes[0]["old_maintainer"] == "old maintainer"

    def test_maintainer_removed_with_non_existing(self):
        changes = []
        original = {"maintainer": "old maintainer"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer"
        assert changes[0]["method"] == "remove"

    def test_maintainer_email_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"maintainer_email": "new@example.com"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer_email"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_maintainer_email"] == "new@example.com"

    def test_maintainer_email_changed(self):
        changes = []
        original = {"maintainer_email": "old@example.com"}
        new = {"maintainer_email": "new@example.com"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer_email"
        assert changes[0]["method"] == "change"
        assert changes[0]["new_maintainer_email"] == "new@example.com"
        assert changes[0]["old_maintainer_email"] == "old@example.com"

    def test_maintainer_email_removed_with_non_existing(self):
        changes = []
        original = {"maintainer_email": "old@example.com"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "maintainer_email"
        assert changes[0]["method"] == "remove"

    def test_author_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"author": "new author"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "author"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_author"] == "new author"

    def test_author_changed(self):
        changes = []
        original = {"author": "old author"}
        new = {"author": "new author"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "author"
        assert changes[0]["method"] == "change"
        assert changes[0]["new_author"] == "new author"
        assert changes[0]["old_author"] == "old author"

    def test_author_removed_with_non_existing(self):
        changes = []
        original = {"author": "old author"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "author"
        assert changes[0]["method"] == "remove"

    def test_author_email_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"author_email": "new@example.com"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "author_email"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_author_email"] == "new@example.com"

    def test_author_email_changed(self):
        changes = []
        original = {"author_email": "old@example.com"}
        new = {"author_email": "new@example.com"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "author_email"
        assert changes[0]["method"] == "change"
        assert changes[0]["new_author_email"] == "new@example.com"
        assert changes[0]["old_author_email"] == "old@example.com"

    def test_author_email_removed_with_non_existing(self):
        changes = []
        original = {"author_email": "old@example.com"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "author_email"
        assert changes[0]["method"] == "remove"

    def test_notes_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"notes": "new notes"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "notes"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_notes"] == "new notes"

    def test_notes_changed(self):
        changes = []
        original = {"notes": "old notes"}
        new = {"notes": "new notes"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "notes"
        assert changes[0]["method"] == "change"
        assert changes[0]["new_notes"] == "new notes"
        assert changes[0]["old_notes"] == "old notes"

    def test_notes_removed_with_non_existing(self):
        changes = []
        original = {"notes": "old notes"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == "notes"
        assert changes[0]["method"] == "remove"

    def test_tag_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"tags": [{"name": "rivers"}]}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "tags"
        assert changes[0]["method"] == "add_one"
        assert changes[0]["tag"] == "rivers"

    def test_multiple_tags_added_when_it_does_not_exist(self):
        changes = []
        original = {"tags": [{"name": "rivers"}]}
        new = {
            "tags": [
                {"name": "rivers"},
                {"name": "oceans"},
                {"name": "streams"},
            ]
        }

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "tags"
        assert changes[0]["method"] == "add_multiple"
        assert set(changes[0]["tags"]) == set(("oceans", "streams"))

    def test_tag_removed_with_non_existing(self):
        changes = []
        original = {"tags": [{"name": "oceans"}]}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "tags"
        assert changes[0]["method"] == "remove_one"
        assert changes[0]["tag"] == "oceans"

    def test_multiple_tags_removed_with_non_existing(self):
        changes = []
        original = {
            "tags": [
                {"name": "rivers"},
                {"name": "oceans"},
                {"name": "streams"},
            ]
        }

        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "tags"
        assert changes[0]["method"] == "remove_multiple"
        assert set(changes[0]["tags"]) == set(("rivers", "oceans", "streams"))

    def test_license_title_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"license_title": "new license"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "license"
        assert changes[0]["new_title"] == "new license"

    def test_license_title_changed(self):
        changes = []
        original = {"license_title": "old license"}
        new = {"license_title": "new license"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "license"
        assert changes[0]["old_title"] == "old license"
        assert changes[0]["new_title"] == "new license"

    def test_license_title_removed_with_non_existing(self):
        changes = []
        original = {"license_title": "old license"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "license"
        assert changes[0]["old_title"] == "old license"
        assert changes[0]["new_title"] is None

    def test_url_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"url": "http://example.com"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "url"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_url"] == "http://example.com"

    def test_url_changed(self):
        changes = []
        original = {"url": "http://example.com"}
        new = {"url": "http://example.com/new"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "url"
        assert changes[0]["method"] == "change"
        assert changes[0]["old_url"] == "http://example.com"
        assert changes[0]["new_url"] == "http://example.com/new"

    def test_url_removed_with_non_existing(self):
        changes = []
        original = {"url": "http://example.com"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "url"
        assert changes[0]["method"] == "remove"
        assert changes[0]["old_url"] == "http://example.com"

    def test_version_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {"version": "1"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "version"
        assert changes[0]["method"] == "add"
        assert changes[0]["new_version"] == "1"

    def test_version_changed(self):
        changes = []
        original = {"version": "1"}
        new = {"version": "2"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "version"
        assert changes[0]["method"] == "change"
        assert changes[0]["old_version"] == "1"
        assert changes[0]["new_version"] == "2"

    def test_version_removed_with_non_existing(self):
        changes = []
        original = {"version": "1"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == "version"
        assert changes[0]["method"] == "remove"
        assert changes[0]["old_version"] == "1"
