# encoding: utf-8

import copy

import pytest
from ckan.lib.changes import check_metadata_changes, check_resource_changes
from ckan.tests import helpers
from ckan.tests.factories import Dataset, Organization, Group


def _new_pkg(new):
    return {u"pkg_id": new["id"], u"name": new["name"], u"title": new["title"]}


@pytest.mark.usefixtures(u"clean_db")
class TestChanges(object):
    def test_title(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch", id=original["id"], title=u"New title"
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"title"
        assert changes[0]["old_title"] == u"Test Dataset"
        assert changes[0]["new_title"] == u"New title"

    def test_name(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch", id=original["id"], name=u"new-name"
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"name"
        assert changes[0]["old_name"] == original["name"]
        assert changes[0]["new_name"] == u"new-name"

    def test_add_extra(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            extras=[{u"key": u"subject", u"value": u"science"}],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"extra_fields"
        assert changes[0]["method"] == u"add_one_value"
        assert changes[0]["key"] == u"subject"
        assert changes[0]["value"] == u"science"

    # TODO how to test 'add_one_no_value'?

    def test_add_multiple_extras(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            extras=[
                {u"key": u"subject", u"value": u"science"},
                {u"key": u"topic", u"value": u"wind"},
            ],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"extra_fields"
        assert changes[0]["method"] == u"add_multiple"
        assert set(changes[0]["key_list"]) == set([u"subject", u"topic"])

    def test_change_extra(self):
        changes = []
        original = Dataset(
            extras=[
                {u"key": u"subject", u"value": u"science"},
                {u"key": u"topic", u"value": u"wind"},
            ]
        )
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            extras=[
                {u"key": u"subject", u"value": u"scientific"},
                {u"key": u"topic", u"value": u"wind"},
            ],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"extra_fields"
        assert changes[0]["method"] == u"change_with_old_value"
        assert changes[0]["key"] == u"subject"
        assert changes[0]["old_value"] == u"science"
        assert changes[0]["new_value"] == u"scientific"

    def test_change_multiple_extras(self):
        changes = []
        original = Dataset(
            extras=[
                {u"key": u"subject", u"value": u"science"},
                {u"key": u"topic", u"value": u"wind"},
            ]
        )
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            extras=[
                {u"key": u"subject", u"value": u"scientific"},
                {u"key": u"topic", u"value": u"rain"},
            ],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 2, changes
        for change in changes:
            assert change["type"] == u"extra_fields"
            assert change["method"] == u"change_with_old_value"
            if change["key"] == u"subject":
                assert change["new_value"] == u"scientific"
            else:
                assert change["key"] == u"topic"
                assert change["new_value"] == u"rain"

    # TODO how to test change2?

    def test_delete_extra(self):
        changes = []
        original = Dataset(
            extras=[
                {u"key": u"subject", u"value": u"science"},
                {u"key": u"topic", u"value": u"wind"},
            ]
        )
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            extras=[{u"key": u"topic", u"value": u"wind"}],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"extra_fields"
        assert changes[0]["method"] == u"remove_one"
        assert changes[0]["key"] == u"subject"

    def test_delete_multiple_extras(self):
        changes = []
        original = Dataset(
            extras=[
                {u"key": u"subject", u"value": u"science"},
                {u"key": u"topic", u"value": u"wind"},
                {u"key": u"geography", u"value": u"global"},
            ]
        )
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            extras=[{u"key": u"topic", u"value": u"wind"}],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"extra_fields"
        assert changes[0]["method"] == u"remove_multiple"
        assert set(changes[0]["key_list"]) == set((u"subject", u"geography"))

    def test_add_maintainer(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch", id=original["id"], maintainer=u"new maintainer"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_maintainer"] == u"new maintainer"

    def test_change_maintainer(self):
        changes = []
        original = Dataset(maintainer=u"first maintainer")
        new = helpers.call_action(
            u"package_patch", id=original["id"], maintainer=u"new maintainer"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer"
        assert changes[0]["method"] == u"change"
        assert changes[0]["old_maintainer"] == u"first maintainer"
        assert changes[0]["new_maintainer"] == u"new maintainer"

    def test_remove_maintainer(self):
        changes = []
        original = Dataset(maintainer=u"first maintainer")
        new = helpers.call_action(
            u"package_patch", id=original["id"], maintainer=u""
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer"
        assert changes[0]["method"] == u"remove"

    def test_add_notes(self):
        changes = []
        original = Dataset(notes=u"")
        new = helpers.call_action(
            u"package_patch", id=original["id"], notes=u"new notes"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"notes"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_notes"] == u"new notes"

    def test_change_notes(self):
        changes = []
        original = Dataset(notes=u"first notes")
        new = helpers.call_action(
            u"package_patch", id=original["id"], notes=u"new notes"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"notes"
        assert changes[0]["method"] == u"change"
        assert changes[0]["old_notes"] == u"first notes"
        assert changes[0]["new_notes"] == u"new notes"

    def test_remove_notes(self):
        changes = []
        original = Dataset(notes=u"first notes")
        new = helpers.call_action(
            u"package_patch", id=original["id"], notes=u""
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"notes"
        assert changes[0]["method"] == u"remove"

    @pytest.mark.ckan_config(u"ckan.auth.create_unowned_dataset", True)
    @pytest.mark.usefixtures(u"with_request_context")
    def test_add_org(self):
        changes = []
        original = Dataset(owner_org=None)
        new_org = Organization()
        new = helpers.call_action(
            u"package_patch", id=original["id"], owner_org=new_org["id"]
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"org"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_org_id"] == new_org["id"]

    @pytest.mark.usefixtures(u"with_request_context")
    def test_change_org(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org["id"])
        new_org = Organization()
        new = helpers.call_action(
            u"package_patch", id=original["id"], owner_org=new_org["id"]
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"org"
        assert changes[0]["method"] == u"change"
        assert changes[0]["old_org_id"] == original["organization"]["id"]
        assert changes[0]["new_org_id"] == new_org["id"]

    @pytest.mark.ckan_config(u"ckan.auth.create_unowned_dataset", True)
    @pytest.mark.usefixtures(u"with_request_context")
    def test_remove_org(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org["id"])

        import ckan.model as model

        pkg = model.Package.get(original["id"])
        pkg.owner_org = None
        pkg.save()

        new = helpers.call_action(u"package_show", id=original["id"])

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"org"
        assert changes[0]["method"] == u"remove"

    @pytest.mark.usefixtures(u"with_request_context")
    def test_make_private(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org["id"], private=False)
        new = helpers.call_action(
            u"package_patch", id=original["id"], private=True
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"private"
        assert changes[0]["new"] == u"Private"

    @pytest.mark.usefixtures(u"with_request_context")
    def test_make_public(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org["id"], private=True)
        new = helpers.call_action(
            u"package_patch", id=original["id"], private=False
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"private"
        assert changes[0]["new"] == u"Public"

    def test_add_tag(self):
        changes = []
        original = Dataset(tags=[{u"name": u"rivers"}])
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            tags=[{u"name": u"rivers"}, {u"name": u"oceans"}],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"tags"
        assert changes[0]["method"] == u"add_one"
        assert changes[0]["tag"] == u"oceans"

    def test_add_multiple_tags(self):
        changes = []
        original = Dataset(tags=[{u"name": u"rivers"}])
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            tags=[
                {u"name": u"rivers"},
                {u"name": u"oceans"},
                {u"name": u"streams"},
            ],
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"tags"
        assert changes[0]["method"] == u"add_multiple"
        assert set(changes[0]["tags"]) == set((u"oceans", u"streams"))

    def test_delete_tag(self):
        changes = []
        original = Dataset(tags=[{u"name": u"rivers"}, {u"name": u"oceans"}])
        new = helpers.call_action(
            u"package_patch", id=original["id"], tags=[{u"name": u"rivers"}]
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"tags"
        assert changes[0]["method"] == u"remove_one"
        assert changes[0]["tag"] == u"oceans"

    def test_remove_multiple_tags(self):
        changes = []
        original = Dataset(
            tags=[
                {u"name": u"rivers"},
                {u"name": u"oceans"},
                {u"name": u"streams"},
            ]
        )
        new = helpers.call_action(
            u"package_patch", id=original["id"], tags=[{u"name": u"rivers"}]
        )

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"tags"
        assert changes[0]["method"] == u"remove_multiple"
        assert set(changes[0]["tags"]) == set((u"oceans", u"streams"))

    def test_add_url(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch", id=original["id"], url=u"new url"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"url"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_url"] == u"new url"

    def test_change_url(self):
        changes = []
        original = Dataset(url=u"first url")
        new = helpers.call_action(
            u"package_patch", id=original["id"], url=u"new url"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"url"
        assert changes[0]["method"] == u"change"
        assert changes[0]["old_url"] == u"first url"
        assert changes[0]["new_url"] == u"new url"

    def test_remove_url(self):
        changes = []
        original = Dataset(url=u"first url")
        new = helpers.call_action(u"package_patch", id=original["id"], url=u"")

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"url"
        assert changes[0]["method"] == u"remove"

    def test_add_version(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch", id=original["id"], version=u"new version"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"version"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_version"] == u"new version"

    def test_change_version(self):
        changes = []
        original = Dataset(version=u"first version")
        new = helpers.call_action(
            u"package_patch", id=original["id"], version=u"new version"
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"version"
        assert changes[0]["method"] == u"change"
        assert changes[0]["old_version"] == u"first version"
        assert changes[0]["new_version"] == u"new version"

    def test_remove_version(self):
        changes = []
        original = Dataset(version=u"first version")
        new = helpers.call_action(
            u"package_patch", id=original["id"], version=u""
        )

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"version"
        assert changes[0]["method"] == u"remove"

    def test_add_resource(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                }
            ],
        )

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"new_resource"
        assert changes[0]["resource_name"] == u"Image 1"

    def test_add_multiple_resources(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u"package_patch",
            id=original["id"],
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                },
                {
                    u"url": u"http://example.com/image2.png",
                    u"format": u"png",
                    u"name": u"Image 2",
                },
            ],
        )

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 2, changes
        assert changes[0]["type"] == u"new_resource"
        assert changes[1]["type"] == u"new_resource"
        if changes[0]["resource_name"] == u"Image 1":
            assert changes[1]["resource_name"] == u"Image 2"
        else:
            assert changes[1]["resource_name"] == u"Image 1"
            assert changes[0]["resource_name"] == u"Image 2"

    def test_change_resource_url(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 2",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][1][u"url"] = u"http://example.com/image_changed.png"
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"new_file"
        assert changes[0]["resource_name"] == u"Image 2"

    def test_change_resource_format(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 2",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][1]["format"] = u"jpg"
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"resource_format"
        assert changes[0]["resource_name"] == u"Image 2"

    def test_change_resource_name(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 2",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][1]["name"] = u"Image changed"
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"resource_name"
        assert changes[0]["old_resource_name"] == u"Image 2"
        assert changes[0]["new_resource_name"] == u"Image changed"

    def test_change_resource_description(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                    u"description": u"First image",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 2",
                    u"description": u"Second image",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][1]["description"] = u"changed"
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"resource_desc"
        assert changes[0]["method"] == u"change"
        assert changes[0]["resource_name"] == u"Image 2"

    def test_add_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                }
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][0]["new key"] = u"new value"
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"resource_extras"
        assert changes[0]["method"] == u"add_one_value"
        assert changes[0]["key"] == u"new key"
        assert changes[0]["value"] == u"new value"

    def test_change_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                    u"key1": u"value1",
                }
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][0]["key1"] = u"new value"
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"resource_extras"
        assert changes[0]["method"] == u"change_value_with_old"
        assert changes[0]["key"] == u"key1"
        assert changes[0]["old_value"] == u"value1"
        assert changes[0]["new_value"] == u"new value"

    def test_remove_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                    u"key1": u"value1",
                }
            ]
        )
        new = copy.deepcopy(original)
        del new["resources"][0]["key1"]
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"resource_extras"
        assert changes[0]["method"] == u"remove_one"
        assert changes[0]["key"] == u"key1"

    def test_change_multiple_resources(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 2",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 3",
                },
            ]
        )
        new = copy.deepcopy(original)
        new["resources"][0]["name"] = u"changed-1"
        new["resources"][1]["name"] = u"changed-2"
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 2, changes
        assert changes[0]["type"] == u"resource_name"
        assert changes[1]["type"] == u"resource_name"
        if changes[0]["old_resource_name"] == u"Image 1":
            assert changes[0]["new_resource_name"] == u"changed-1"
        else:
            assert changes[0]["old_resource_name"] == u"Image 2"
            assert changes[0]["new_resource_name"] == u"changed-2"

    def test_delete_resource(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 2",
                },
            ]
        )
        new = copy.deepcopy(original)
        del new["resources"][0]
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"delete_resource"
        assert changes[0]["resource_name"] == u"Image 1"

    def test_delete_multiple_resources(self):
        changes = []
        original = Dataset(
            resources=[
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 1",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 2",
                },
                {
                    u"url": u"http://example.com/image.png",
                    u"format": u"png",
                    u"name": u"Image 3",
                },
            ]
        )
        new = copy.deepcopy(original)
        del new["resources"][1]
        del new["resources"][0]
        new = helpers.call_action(u"package_update", **new)

        check_resource_changes(changes, original, new, u"fake")

        assert len(changes) == 2, changes
        assert changes[0]["type"] == u"delete_resource"
        if changes[0]["resource_name"] == u"Image 1":
            assert changes[1]["resource_name"] == u"Image 2"
        else:
            assert changes[0]["resource_name"] == u"Image 2"
            assert changes[1]["resource_name"] == u"Image 1"


class TestChangesWithSingleAttributes(object):

    def test_title_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u'title': u"new title"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"title"
        assert changes[0]["old_title"] is None
        assert changes[0]["new_title"] == u"new title"

    def test_title_changed(self):
        changes = []
        original = {u'title': u'old title'}
        new = {u'title': u"new title"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"title"
        assert changes[0]["old_title"] == u"old title"
        assert changes[0]["new_title"] == u"new title"

    def test_title_removed_with_non_existing(self):
        changes = []
        original = {u'title': u'old title'}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"title"
        assert changes[0]["old_title"] == u'old title'
        assert changes[0]["new_title"] is None

    def test_owner_org_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new_org = {u'id': u'new_org_id'}
        new = {u'owner_org': new_org['id'], u'organization': new_org}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"org"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_org_id"] == new_org['id']

    def test_owner_org_changed(self):
        changes = []
        old_org = {u'id': u'old_org_id'}
        original = {u'owner_org': old_org['id'], u'organization': old_org}
        new_org = {u'id': u'new_org_id'}
        new = {u'owner_org': new_org['id'], u'organization': new_org}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"org"
        assert changes[0]["method"] == u"change"
        assert changes[0]["old_org_id"] == old_org['id']
        assert changes[0]["new_org_id"] == new_org['id']

    def test_owner_org_removed_with_non_existing(self):
        changes = []
        old_org = {u'id': u'org_id'}
        original = {u'owner_org': old_org['id'], u'organization': old_org}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"org"
        assert changes[0]["method"] == u"remove"
        assert changes[0]["old_org_id"] == old_org['id']

    def test_maintainer_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u'maintainer': u"new maintainer"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_maintainer"] == u"new maintainer"

    def test_maintainer_changed(self):
        changes = []
        original = {u'maintainer': u"old maintainer"}
        new = {u'maintainer': u"new maintainer"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer"
        assert changes[0]["method"] == u"change"
        assert changes[0]["new_maintainer"] == u"new maintainer"
        assert changes[0]["old_maintainer"] == u"old maintainer"

    def test_maintainer_removed_with_non_existing(self):
        changes = []
        original = {u'maintainer': u"old maintainer"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer"
        assert changes[0]["method"] == u"remove"

    def test_maintainer_email_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u'maintainer_email': u"new@example.com"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer_email"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_maintainer_email"] == u"new@example.com"

    def test_maintainer_email_changed(self):
        changes = []
        original = {u'maintainer_email': u"old@example.com"}
        new = {u'maintainer_email': u"new@example.com"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer_email"
        assert changes[0]["method"] == u"change"
        assert changes[0]["new_maintainer_email"] == u"new@example.com"
        assert changes[0]["old_maintainer_email"] == u"old@example.com"

    def test_maintainer_email_removed_with_non_existing(self):
        changes = []
        original = {u'maintainer_email': u"old@example.com"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"maintainer_email"
        assert changes[0]["method"] == u"remove"

    def test_author_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u'author': u"new author"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"author"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_author"] == u"new author"

    def test_author_changed(self):
        changes = []
        original = {u'author': u"old author"}
        new = {u'author': u"new author"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"author"
        assert changes[0]["method"] == u"change"
        assert changes[0]["new_author"] == u"new author"
        assert changes[0]["old_author"] == u"old author"

    def test_author_removed_with_non_existing(self):
        changes = []
        original = {u'author': u"old author"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"author"
        assert changes[0]["method"] == u"remove"

    def test_author_email_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u'author_email': u"new@example.com"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"author_email"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_author_email"] == u"new@example.com"

    def test_author_email_changed(self):
        changes = []
        original = {u'author_email': u"old@example.com"}
        new = {u'author_email': u"new@example.com"}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"author_email"
        assert changes[0]["method"] == u"change"
        assert changes[0]["new_author_email"] == u"new@example.com"
        assert changes[0]["old_author_email"] == u"old@example.com"

    def test_author_email_removed_with_non_existing(self):
        changes = []
        original = {u'author_email': u"old@example.com"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"author_email"
        assert changes[0]["method"] == u"remove"

    def test_notes_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u'notes': u'new notes'}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"notes"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_notes"] == u"new notes"

    def test_notes_changed(self):
        changes = []
        original = {u'notes': u'old notes'}
        new = {u'notes': u'new notes'}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"notes"
        assert changes[0]["method"] == u"change"
        assert changes[0]["new_notes"] == u"new notes"
        assert changes[0]["old_notes"] == u"old notes"

    def test_notes_removed_with_non_existing(self):
        changes = []
        original = {u'notes': u'old notes'}
        new = {}

        check_metadata_changes(changes, original, new)

        assert changes[0]["type"] == u"notes"
        assert changes[0]["method"] == u"remove"

    def test_tag_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u"tags": [{u"name": u"rivers"}]}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"tags"
        assert changes[0]["method"] == u"add_one"
        assert changes[0]["tag"] == u"rivers"

    def test_multiple_tags_added_when_it_does_not_exist(self):
        changes = []
        original = {u"tags": [{u"name": u"rivers"}]}
        new = {u"tags": [
            {u"name": u"rivers"},
            {u"name": u"oceans"},
            {u"name": u"streams"},
        ]}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"tags"
        assert changes[0]["method"] == u"add_multiple"
        assert set(changes[0]["tags"]) == set((u"oceans", u"streams"))

    def test_tag_removed_with_non_existing(self):
        changes = []
        original = {u"tags": [{u"name": u"oceans"}]}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"tags"
        assert changes[0]["method"] == u"remove_one"
        assert changes[0]["tag"] == u"oceans"

    def test_multiple_tags_removed_with_non_existing(self):
        changes = []
        original = {u"tags": [
            {u"name": u"rivers"},
            {u"name": u"oceans"},
            {u"name": u"streams"},
        ]}

        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"tags"
        assert changes[0]["method"] == u"remove_multiple"
        assert set(changes[0]["tags"]) == set((u"rivers", u"oceans", u"streams"))

    def test_license_title_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u"license_title": u"new license"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"license"
        assert changes[0]["new_title"] == u"new license"

    def test_license_title_changed(self):
        changes = []
        original = {u"license_title": u"old license"}
        new = {u"license_title": u"new license"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"license"
        assert changes[0]["old_title"] == u"old license"
        assert changes[0]["new_title"] == u"new license"

    def test_license_title_removed_with_non_existing(self):
        changes = []
        original = {u"license_title": u"old license"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"license"
        assert changes[0]["old_title"] == u"old license"
        assert changes[0]["new_title"] is None

    def test_url_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u'url': u'http://example.com'}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"url"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_url"] == u'http://example.com'

    def test_url_changed(self):
        changes = []
        original = {u"url": u"http://example.com"}
        new = {u"url": u"http://example.com/new"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"url"
        assert changes[0]["method"] == u"change"
        assert changes[0]["old_url"] == u"http://example.com"
        assert changes[0]["new_url"] == u"http://example.com/new"

    def test_url_removed_with_non_existing(self):
        changes = []
        original = {u"url": u"http://example.com"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"url"
        assert changes[0]["method"] == u"remove"
        assert changes[0]["old_url"] == u"http://example.com"

    def test_version_added_when_it_does_not_exist(self):
        changes = []
        original = {}
        new = {u'version': u'1'}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"version"
        assert changes[0]["method"] == u"add"
        assert changes[0]["new_version"] == u'1'

    def test_version_changed(self):
        changes = []
        original = {u"version": u"1"}
        new = {u"version": u"2"}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"version"
        assert changes[0]["method"] == u"change"
        assert changes[0]["old_version"] == u"1"
        assert changes[0]["new_version"] == u"2"

    def test_version_removed_with_non_existing(self):
        changes = []
        original = {u"version": u"1"}
        new = {}

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        assert changes[0]["type"] == u"version"
        assert changes[0]["method"] == u"remove"
        assert changes[0]["old_version"] == u"1"
