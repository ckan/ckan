# -*- coding: utf-8 -*-

import datetime
import re

import pytest

from ckan import model
import ckan.logic as logic
import ckan.logic.schema as schema
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan import __version__
from ckan.lib.search.common import SearchError


@pytest.mark.usefixtures("non_clean_db")
class TestPackageShow(object):
    def test_package_show(self):
        # simple dataset, simple checks
        dataset1 = factories.Dataset()

        dataset2 = helpers.call_action("package_show", id=dataset1["id"])

        assert dataset2["name"] == dataset1["name"]
        missing_keys = set(("title", "groups")) - set(dataset2.keys())
        assert not missing_keys, missing_keys

    def test_package_show_with_full_dataset(self):
        # an full dataset
        org = factories.Organization()
        group = factories.Group()
        dataset1 = factories.Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                }
            ],
            tags=[{"name": factories.Tag.stub().name}],
            extras=[{"key": "subject", "value": "science"}],
            groups=[{"id": group["id"]}],
            owner_org=org["id"],
        )
        dataset2 = helpers.call_action("package_show", id=dataset1["id"])

        # checking the whole dataset is a bit brittle as a test, but it
        # documents what the package_dict is clearly and tracks how it changes
        # as CKAN changes over time.

        # fix values which change every time you run this test
        def replace_uuid(dict_, key):
            assert key in dict_
            dict_[key] = "<SOME-UUID>"

        def replace_datetime(dict_, key):
            assert key in dict_
            dict_[key] = "2019-05-24T15:52:30.123456"

        def replace_number_suffix(dict_, key):
            # e.g. "Test Dataset 23" -> "Test Dataset "
            assert key in dict_
            dict_[key] = re.sub(r"\d+$", "num", dict_[key])

        replace_uuid(dataset2, "id")
        replace_uuid(dataset2, "creator_user_id")
        replace_uuid(dataset2, "owner_org")
        replace_number_suffix(dataset2, "name")
        replace_datetime(dataset2, "metadata_created")
        replace_datetime(dataset2, "metadata_modified")
        replace_datetime(dataset2["resources"][0], "metadata_modified")
        replace_uuid(dataset2["groups"][0], "id")
        replace_number_suffix(dataset2["groups"][0], "name")
        replace_number_suffix(dataset2["groups"][0], "title")
        replace_number_suffix(dataset2["groups"][0], "display_name")
        replace_uuid(dataset2["organization"], "id")
        replace_number_suffix(dataset2["organization"], "name")
        replace_number_suffix(dataset2["organization"], "title")
        replace_datetime(dataset2["organization"], "created")
        replace_uuid(dataset2["resources"][0], "id")
        replace_uuid(dataset2["resources"][0], "package_id")
        replace_number_suffix(dataset2["resources"][0], "name")
        replace_datetime(dataset2["resources"][0], "created")
        replace_uuid(dataset2["tags"][0], "id")

        assert dataset2 == {
            "author": dataset1["author"],
            "author_email": dataset1["author_email"],
            "creator_user_id": "<SOME-UUID>",
            "extras": dataset1["extras"],
            "groups": [
                {
                    "description": group["description"],
                    "display_name": group["display_name"],
                    "id": "<SOME-UUID>",
                    "image_display_url": group["image_display_url"],
                    "name": group["name"],
                    "title": group["title"],
                }
            ],
            "id": "<SOME-UUID>",
            "isopen": dataset1["isopen"],
            "license_id": dataset1["license_id"],
            "license_title": dataset1["license_title"],
            "maintainer": dataset1["maintainer"],
            "maintainer_email": dataset1["maintainer_email"],
            "metadata_created": "2019-05-24T15:52:30.123456",
            "metadata_modified": "2019-05-24T15:52:30.123456",
            "name": dataset1["name"],
            "notes": dataset1["notes"],
            "num_resources": dataset1["num_resources"],
            "num_tags": dataset1["num_tags"],
            "organization": {
                "approval_status": org["approval_status"],
                "created": "2019-05-24T15:52:30.123456",
                "description": org["description"],
                "id": "<SOME-UUID>",
                "image_url": org["image_url"],
                "is_organization": org["is_organization"],
                "name": org["name"],
                "state": org["state"],
                "title": org["title"],
                "type": org["type"],
            },
            "owner_org": "<SOME-UUID>",
            "private": dataset1["private"],
            "relationships_as_object": dataset1["relationships_as_object"],
            "relationships_as_subject": dataset1["relationships_as_subject"],
            "resources": [
                {
                    "cache_last_updated": None,
                    "cache_url": dataset1["resources"][0]["cache_url"],
                    "created": "2019-05-24T15:52:30.123456",
                    "description": dataset1["resources"][0]["description"],
                    "format": dataset1["resources"][0]["format"],
                    "hash": "",
                    "id": "<SOME-UUID>",
                    "last_modified": dataset1["resources"][0]["last_modified"],
                    "metadata_modified": "2019-05-24T15:52:30.123456",
                    "mimetype": dataset1["resources"][0]["mimetype"],
                    "mimetype_inner": None,
                    "name": "Image num",
                    "package_id": "<SOME-UUID>",
                    "position": dataset1["resources"][0]["position"],
                    "resource_type": dataset1["resources"][0]["resource_type"],
                    "size": dataset1["resources"][0]["size"],
                    "state": dataset1["resources"][0]["state"],
                    "url": dataset1["resources"][0]["url"],
                    "url_type": dataset1["resources"][0]["url_type"],
                }
            ],
            "state": dataset1["state"],
            "tags": [
                {
                    "display_name": dataset1["tags"][0]["display_name"],
                    "id": "<SOME-UUID>",
                    "name": dataset1["tags"][0]["name"],
                    "state": dataset1["tags"][0]["state"],
                    "vocabulary_id": dataset1["tags"][0]["vocabulary_id"],
                }
            ],
            "title": dataset1["title"],
            "type": dataset1["type"],
            "url": dataset1["url"],
            "version": dataset1["version"],
        }

    def test_package_show_with_custom_schema(self):
        dataset1 = factories.Dataset()
        from ckan.logic.schema import default_show_package_schema

        custom_schema = default_show_package_schema()

        def foo(key, data, errors, context):  # noqa
            data[key] = "foo"

        custom_schema["new_field"] = [foo]

        dataset2 = helpers.call_action(
            "package_show",
            id=dataset1["id"],
            context={"schema": custom_schema},
        )

        assert dataset2["new_field"] == "foo"

    def test_package_show_with_custom_schema_return_default_schema(self):
        dataset1 = factories.Dataset()
        from ckan.logic.schema import default_show_package_schema

        custom_schema = default_show_package_schema()

        def foo(key, data, errors, context):  # noqa
            data[key] = "foo"

        custom_schema["new_field"] = [foo]

        dataset2 = helpers.call_action(
            "package_show",
            id=dataset1["id"],
            use_default_schema=True,
            context={"schema": custom_schema},
        )

        assert "new_field" not in dataset2


@pytest.mark.usefixtures("clean_db")
class TestGroupList(object):
    def test_group_list(self):

        group1 = factories.Group()
        group2 = factories.Group()

        group_list = helpers.call_action("group_list")

        assert sorted(group_list) == sorted(
            [g["name"] for g in [group1, group2]]
        )

    def test_group_list_in_presence_of_organizations(self):
        """
        Getting the group_list should only return groups of type 'group' (not
        organizations).
        """
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Organization()
        factories.Organization()

        group_list = helpers.call_action("group_list")

        assert sorted(group_list) == sorted(
            [g["name"] for g in [group1, group2]]
        )

    def test_group_list_in_presence_of_custom_group_types(self):
        """Getting the group_list shouldn't return custom group types."""
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Group(type="custom")

        group_list = helpers.call_action("group_list")

        assert sorted(group_list) == sorted(
            [g["name"] for g in [group1, group2]]
        )

    def test_group_list_return_custom_group(self):
        """
        Getting the group_list with a type defined should only return
        groups of that type.
        """
        group1 = factories.Group(type="custom")
        group2 = factories.Group(type="custom")
        factories.Group()
        factories.Group()

        group_list = helpers.call_action("group_list", type="custom")

        assert sorted(group_list) == sorted(
            [g["name"] for g in [group1, group2]]
        )

    def test_group_list_sort_by_package_count(self):

        factories.Group(name="aa")
        factories.Group(name="bb")
        factories.Dataset(groups=[{"name": "aa"}, {"name": "bb"}])
        factories.Dataset(groups=[{"name": "bb"}])

        group_list = helpers.call_action("group_list", sort="package_count")
        assert sorted(group_list) == sorted(["bb", "aa"])

    def test_group_list_sort_by_package_count_ascending(self):

        factories.Group(name="aa")
        factories.Group(name="bb")
        factories.Dataset(groups=[{"name": "aa"}, {"name": "bb"}])
        factories.Dataset(groups=[{"name": "aa"}])

        group_list = helpers.call_action(
            "group_list", sort="package_count asc"
        )

        assert group_list == ["bb", "aa"]

    def test_group_list_sort_default(self):

        factories.Group(name="zz", title="aa")
        factories.Group(name="yy", title="bb")

        group_list = helpers.call_action("group_list")

        assert group_list == ["zz", "yy"]

    @pytest.mark.ckan_config("ckan.default_group_sort", "name")
    def test_group_list_sort_from_config(self):

        factories.Group(name="zz", title="aa")
        factories.Group(name="yy", title="bb")

        group_list = helpers.call_action("group_list")

        assert group_list == ["yy", "zz"]

    def eq_expected(self, expected_dict, result_dict):
        superfluous_keys = set(result_dict) - set(expected_dict)
        assert not superfluous_keys, "Did not expect key: %s" % " ".join(
            ("%s=%s" % (k, result_dict[k]) for k in superfluous_keys)
        )
        for key in expected_dict:
            assert (
                expected_dict[key] == result_dict[key]
            ), "%s=%s should be %s" % (
                key,
                result_dict[key],
                expected_dict[key],
            )

    def test_group_list_all_fields(self):

        group = factories.Group()

        group_list = helpers.call_action("group_list", all_fields=True)

        expected_group = dict(group)
        for field in ("users", "tags", "extras", "groups"):
            del expected_group[field]

        assert group_list[0] == expected_group
        assert "extras" not in group_list[0]
        assert "tags" not in group_list[0]
        assert "groups" not in group_list[0]
        assert "users" not in group_list[0]
        assert "datasets" not in group_list[0]

    def _create_bulk_groups(self, name, count):

        groups = [
            model.Group(name="{}_{}".format(name, i)) for i in range(count)
        ]
        model.Session.add_all(groups)
        model.repo.commit_and_remove()

    def test_limit_default(self):
        self._create_bulk_groups("group_default", 1010)
        results = helpers.call_action("group_list")
        assert len(results) == 1000  # i.e. default value

    @pytest.mark.ckan_config("ckan.group_and_organization_list_max", "5")
    def test_limit_configured(self):
        self._create_bulk_groups("group_default", 7)
        results = helpers.call_action("group_list")
        assert len(results) == 5  # i.e. configured limit

    def test_all_fields_limit_default(self):
        self._create_bulk_groups("org_all_fields_default", 30)
        results = helpers.call_action("group_list", all_fields=True)
        assert len(results) == 25  # i.e. default value

    @pytest.mark.ckan_config(
        "ckan.group_and_organization_list_all_fields_max", "5"
    )
    def test_all_fields_limit_configured(self):
        self._create_bulk_groups("org_all_fields_default", 30)
        results = helpers.call_action("group_list", all_fields=True)
        assert len(results) == 5  # i.e. configured limit

    def test_group_list_extras_returned(self):

        group = factories.Group(extras=[{"key": "key1", "value": "val1"}])

        group_list = helpers.call_action(
            "group_list", all_fields=True, include_extras=True
        )

        assert group_list[0]["extras"] == group["extras"]
        assert group_list[0]["extras"][0]["key"] == "key1"

    def test_group_list_users_returned(self):
        user = factories.User()
        group = factories.Group(
            users=[{"name": user["name"], "capacity": "admin"}]
        )

        group_list = helpers.call_action(
            "group_list", all_fields=True, include_users=True
        )

        assert group_list[0]["users"] == group["users"]
        assert group_list[0]["users"][0]["name"] == group["users"][0]["name"]

    # NB there is no test_group_list_tags_returned because tags are not in the
    # group_create schema (yet)

    def test_group_list_groups_returned(self):

        parent_group = factories.Group(tags=[{"name": "river"}])
        child_group = factories.Group(
            groups=[{"name": parent_group["name"]}], tags=[{"name": "river"}]
        )

        group_list = helpers.call_action(
            "group_list", all_fields=True, include_groups=True
        )

        child_group_returned = group_list[0]
        if group_list[0]["name"] == child_group["name"]:
            child_group_returned, _ = group_list
        else:
            child_group_returned, _ = group_list[::-1]
        expected_parent_group = dict(parent_group)

        assert [g["name"] for g in child_group_returned["groups"]] == [
            expected_parent_group["name"]
        ]

    def test_group_list_limit(self):

        group1 = factories.Group(title="aa")
        group2 = factories.Group(title="bb")
        group3 = factories.Group(title="cc")
        group_names = [g["name"] for g in [group1, group2, group3]]

        group_list = helpers.call_action("group_list", limit=1)

        assert len(group_list) == 1
        assert group_list[0] == group_names[0]

    def test_group_list_offset(self):

        group1 = factories.Group(title="aa")
        group2 = factories.Group(title="bb")
        group3 = factories.Group(title="cc")
        group_names = [g["name"] for g in [group1, group2, group3]]

        group_list = helpers.call_action("group_list", offset=2)

        assert len(group_list) == 1
        # group list returns sorted result. This is not necessarily
        # order of creation
        assert group_list[0] == group_names[2]

    def test_group_list_limit_and_offset(self):

        factories.Group(title="aa")
        group2 = factories.Group(title="bb")
        factories.Group(title="cc")

        group_list = helpers.call_action("group_list", offset=1, limit=1)

        assert len(group_list) == 1
        assert group_list[0] == group2["name"]

    def test_group_list_limit_as_string(self):

        factories.Group(name="aa")
        factories.Group(name="bb")

        group_list = helpers.call_action("group_list", limit="1")

        assert len(group_list) == 1

    def test_group_list_wrong_limit(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action("group_list", limit="a")

    def test_group_list_wrong_offset(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action("group_list", offset="-2")


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestGroupShow(object):
    def test_group_show(self):
        group = factories.Group(user=factories.User())

        group_dict = helpers.call_action(
            "group_show", id=group["id"], include_datasets=True
        )

        group_dict.pop("packages", None)
        assert group_dict == group

    def test_group_show_error_not_found(self):

        with pytest.raises(logic.NotFound):
            helpers.call_action("group_show", id="does_not_exist")

    def test_group_show_error_for_organization(self):

        org = factories.Organization()

        with pytest.raises(logic.NotFound):
            helpers.call_action("group_show", id=org["id"])

    def test_group_show_packages_returned(self):
        user_name = helpers.call_action("get_site_user")["name"]

        group = factories.Group(user=factories.User())

        datasets = [
            {"name": "dataset_1", "groups": [{"name": group["name"]}]},
            {"name": "dataset_2", "groups": [{"name": group["name"]}]},
        ]

        for dataset in datasets:
            helpers.call_action(
                "package_create", context={"user": user_name}, **dataset
            )

        group_dict = helpers.call_action(
            "group_show", id=group["id"], include_datasets=True
        )

        assert len(group_dict["packages"]) == 2
        assert group_dict["package_count"] == 2

    def test_group_show_packages_returned_for_view(self):

        user_name = helpers.call_action("get_site_user")["name"]

        group = factories.Group(user=factories.User())

        datasets = [
            {"name": "dataset_1", "groups": [{"name": group["name"]}]},
            {"name": "dataset_2", "groups": [{"name": group["name"]}]},
        ]

        for dataset in datasets:
            helpers.call_action(
                "package_create", context={"user": user_name}, **dataset
            )

        group_dict = helpers.call_action(
            "group_show",
            id=group["id"],
            include_datasets=True,
            context={"for_view": True},
        )

        assert len(group_dict["packages"]) == 2
        assert group_dict["package_count"] == 2

    def test_group_show_no_packages_returned(self):

        user_name = helpers.call_action("get_site_user")["name"]

        group = factories.Group(user=factories.User())

        datasets = [
            {"name": "dataset_1", "groups": [{"name": group["name"]}]},
            {"name": "dataset_2", "groups": [{"name": group["name"]}]},
        ]

        for dataset in datasets:
            helpers.call_action(
                "package_create", context={"user": user_name}, **dataset
            )

        group_dict = helpers.call_action(
            "group_show", id=group["id"], include_datasets=False
        )

        assert "packages" not in group_dict
        assert group_dict["package_count"] == 2

    def test_group_show_does_not_show_private_datasets(self):
        """group_show() should never show private datasets.

        If a dataset is a private member of an organization and also happens to
        be a member of a group, group_show() should not return the dataset as
        part of the group dict, even if the user calling group_show() is a
        member or admin of the group or the organization or is a sysadmin.

        """
        org_member = factories.User()
        org = factories.Organization(user=org_member)
        private_dataset = factories.Dataset(
            user=org_member, owner_org=org["name"], private=True
        )

        group = factories.Group()

        # Add the private dataset to the group.
        helpers.call_action(
            "member_create",
            id=group["id"],
            object=private_dataset["id"],
            object_type="package",
            capacity="public",
        )

        # Create a member user and an admin user of the group.
        group_member = factories.User()
        helpers.call_action(
            "member_create",
            id=group["id"],
            object=group_member["id"],
            object_type="user",
            capacity="member",
        )
        group_admin = factories.User()
        helpers.call_action(
            "member_create",
            id=group["id"],
            object=group_admin["id"],
            object_type="user",
            capacity="admin",
        )

        # Create a user who isn't a member of any group or organization.
        non_member = factories.User()

        sysadmin = factories.Sysadmin()

        # None of the users should see the dataset when they call group_show().
        for user in (
            org_member,
            group_member,
            group_admin,
            non_member,
            sysadmin,
            None,
        ):

            if user is None:
                context = None  # No user logged-in.
            else:
                context = {"user": user["name"]}

            group = helpers.call_action(
                "group_show",
                id=group["id"],
                include_datasets=True,
                context=context,
            )

            assert private_dataset["id"] not in [
                dataset["id"] for dataset in group["packages"]
            ], "group_show() should never show private datasets"

    @pytest.mark.ckan_config("ckan.search.rows_max", "2")
    def test_package_limit_configured(self):
        group = factories.Group()
        for _ in range(3):
            factories.Dataset(groups=[{"id": group["id"]}])
        id = group["id"]

        results = helpers.call_action("group_show", id=id, include_datasets=1)
        assert len(results["packages"]) == 2  # i.e. ckan.search.rows_max


@pytest.mark.usefixtures("clean_db")
class TestOrganizationList(object):
    def test_organization_list(self):

        org1 = factories.Organization()
        org2 = factories.Organization()

        org_list = helpers.call_action("organization_list")

        assert sorted(org_list) == sorted([g["name"] for g in [org1, org2]])

    def test_organization_list_in_presence_of_groups(self):
        """
        Getting the organization_list only returns organization group
        types.
        """
        org1 = factories.Organization()
        org2 = factories.Organization()
        factories.Group()
        factories.Group()

        org_list = helpers.call_action("organization_list")

        assert sorted(org_list) == sorted([g["name"] for g in [org1, org2]])

    def test_organization_list_in_presence_of_custom_group_types(self):
        """
        Getting the organization_list only returns organization group
        types.
        """
        org1 = factories.Organization()
        org2 = factories.Organization()
        factories.Group(type="custom")
        factories.Group(type="custom")

        org_list = helpers.call_action("organization_list")

        assert sorted(org_list) == sorted([g["name"] for g in [org1, org2]])

    def test_organization_list_return_custom_organization_type(self):
        """
        Getting the org_list with a type defined should only return
        orgs of that type.
        """
        factories.Organization()
        org2 = factories.Organization(type="custom_org")
        factories.Group(type="custom")
        factories.Group(type="custom")

        org_list = helpers.call_action("organization_list", type="custom_org")

        assert sorted(org_list) == sorted(
            [g["name"] for g in [org2]]
        ), "{}".format(org_list)

    def _create_bulk_orgs(self, name, count):
        from ckan import model

        orgs = [
            model.Group(
                name="{}_{}".format(name, i),
                is_organization=True,
                type="organization",
            )
            for i in range(count)
        ]

        model.Session.add_all(orgs)
        model.repo.commit_and_remove()

    def test_limit_default(self):
        self._create_bulk_orgs("org_default", 1010)
        results = helpers.call_action("organization_list")
        assert len(results) == 1000  # i.e. default value

    @pytest.mark.ckan_config("ckan.group_and_organization_list_max", 5)
    def test_limit_configured(self):
        self._create_bulk_orgs("org_default", 7)
        results = helpers.call_action("organization_list")
        assert len(results) == 5  # i.e. configured limit

    @pytest.mark.ckan_config("ckan.group_and_organization_list_max", 5)
    def test_limit_with_custom_max_limit(self):
        self._create_bulk_orgs("org_default", 5)
        results = helpers.call_action("organization_list", limit=2)
        assert len(results) == 2

    def test_all_fields_limit_default(self):
        self._create_bulk_orgs("org_all_fields_default", 30)
        results = helpers.call_action("organization_list", all_fields=True)
        assert len(results) == 25  # i.e. default value

    @pytest.mark.ckan_config(
        "ckan.group_and_organization_list_all_fields_max", 5
    )
    def test_all_fields_limit_with_custom_max_limit(self):
        self._create_bulk_orgs("org_all_fields_default", 5)
        results = helpers.call_action(
            "organization_list", all_fields=True, limit=2
        )
        assert len(results) == 2

    @pytest.mark.ckan_config(
        "ckan.group_and_organization_list_all_fields_max", 5
    )
    def test_all_fields_limit_configured(self):
        self._create_bulk_orgs("org_all_fields_default", 30)
        results = helpers.call_action("organization_list", all_fields=True)
        assert len(results) == 5  # i.e. configured limit


@pytest.mark.usefixtures("non_clean_db")
class TestOrganizationShow(object):
    def test_organization_show(self):
        org = factories.Organization()

        org_dict = helpers.call_action(
            "organization_show", id=org["id"], include_datasets=True
        )

        org_dict.pop("packages", None)
        assert org_dict == org

    def test_organization_show_error_not_found(self):

        with pytest.raises(logic.NotFound):
            helpers.call_action("organization_show", id="does_not_exist")

    def test_organization_show_error_for_group(self):

        group = factories.Group()

        with pytest.raises(logic.NotFound):
            helpers.call_action("organization_show", id=group["id"])

    def test_organization_show_packages_returned(self):

        user_name = helpers.call_action("get_site_user")["name"]

        org = factories.Organization()

        datasets = [
            {"name": factories.Dataset.stub().name, "owner_org": org["name"]},
            {"name": factories.Dataset.stub().name, "owner_org": org["name"]},
        ]

        for dataset in datasets:
            helpers.call_action(
                "package_create", context={"user": user_name}, **dataset
            )

        org_dict = helpers.call_action(
            "organization_show", id=org["id"], include_datasets=True
        )

        assert len(org_dict["packages"]) == 2
        assert org_dict["package_count"] == 2

    def test_organization_show_private_packages_not_returned(self):

        user_name = helpers.call_action("get_site_user")["name"]

        org = factories.Organization()
        dataset1 = factories.Dataset.stub().name
        datasets = [
            {"name": dataset1, "owner_org": org["name"]},
            {
                "name": factories.Dataset.stub().name,
                "owner_org": org["name"],
                "private": True,
            },
        ]

        for dataset in datasets:
            helpers.call_action(
                "package_create", context={"user": user_name}, **dataset
            )

        org_dict = helpers.call_action(
            "organization_show", id=org["id"], include_datasets=True
        )

        assert len(org_dict["packages"]) == 1
        assert org_dict["packages"][0]["name"] == dataset1
        assert org_dict["package_count"] == 1

    @pytest.mark.ckan_config("ckan.search.rows_max", "2")
    def test_package_limit_configured(self):
        org = factories.Organization()
        for _ in range(3):
            factories.Dataset(owner_org=org["id"])
        id = org["id"]

        results = helpers.call_action(
            "organization_show", id=id, include_datasets=1
        )
        assert len(results["packages"]) == 2  # i.e. ckan.search.rows_max


@pytest.mark.usefixtures("clean_db")
class TestUserList(object):
    def test_user_list_default_values(self):
        user = factories.User()

        got_users = helpers.call_action("user_list")

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user["id"] == user["id"]
        assert got_user["name"] == user["name"]
        assert got_user["fullname"] == user["fullname"]
        assert got_user["display_name"] == user["display_name"]
        assert got_user["created"] == user["created"]
        assert got_user["about"] == user["about"]
        assert got_user["sysadmin"] == user["sysadmin"]
        assert got_user["number_created_packages"] == 0
        assert "password" not in got_user
        assert "reset_key" not in got_user
        assert "apikey" not in got_user
        assert "email" not in got_user
        assert "datasets" not in got_user

    def test_user_list_edits(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        dataset["title"] = "Edited title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )
        got_users = helpers.call_action("user_list")

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user["number_created_packages"] == 1

    def test_include_site_user(self, ckan_config):
        factories.User()

        users = helpers.call_action("user_list")
        assert len(users) == 1

        users = helpers.call_action("user_list", include_site_user=True)
        assert len(users) == 2

    def test_user_list_excludes_deleted_users(self):
        user = factories.User()
        factories.User(state="deleted")

        got_users = helpers.call_action("user_list")

        assert len(got_users) == 1
        assert got_users[0]["name"] == user["name"]

    def test_user_list_not_all_fields(self):
        user = factories.User()

        got_users = helpers.call_action("user_list", all_fields=False)

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user == user["name"]

    def test_user_list_return_query(self):
        user_a = factories.User(email="a@example.com")
        query = helpers.call_action(
            "user_list",
            {"return_query": True},
            email="a@example.com"
        )
        user = query.one()

        expected = ["name", "fullname", "about", "email"]
        for prop in expected:
            assert user_a[prop] == getattr(user, prop), prop

    def test_user_list_filtered_by_email(self):

        user_a = factories.User(email="a@example.com")
        factories.User(email="b@example.com")

        got_users = helpers.call_action(
            "user_list", email="a@example.com", all_fields=False
        )

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user == user_a["name"]

    def test_user_list_order_by_default(self):
        default_user = helpers.call_action("get_site_user", ignore_auth=True)

        users = [
            factories.User(fullname="Xander Bird", name="bird_x"),
            factories.User(fullname="Max Hankins", name="hankins_m"),
            factories.User(fullname="", name="zoe_w"),
            factories.User(fullname="Kathy Tillman", name="tillman_k"),
        ]
        expected_names = [
            u["name"]
            for u in [
                users[3],  # Kathy Tillman
                users[1],  # Max Hankins
                users[0],  # Xander Bird
                users[2],  # zoe_w
            ]
        ]

        got_users = helpers.call_action("user_list")
        got_names = [
            u["name"] for u in got_users if u["name"] != default_user["name"]
        ]

        assert got_names == expected_names

    def test_user_list_order_by_fullname_only(self):
        default_user = helpers.call_action("get_site_user", ignore_auth=True)

        users = [
            factories.User(fullname="Xander Bird", name="bird_x"),
            factories.User(fullname="Max Hankins", name="hankins_m"),
            factories.User(fullname="", name="morgan_w"),
            factories.User(fullname="Kathy Tillman", name="tillman_k"),
        ]
        expected_fullnames = sorted([u["fullname"] for u in users])

        got_users = helpers.call_action("user_list", order_by="fullname")
        got_fullnames = [
            u["fullname"]
            for u in got_users
            if u["name"] != default_user["name"]
        ]

        assert got_fullnames == expected_fullnames

    def test_user_list_order_by_created_datasets(self):
        default_user = helpers.call_action("get_site_user", ignore_auth=True)

        users = [
            factories.User(fullname="Xander Bird", name="bird_x"),
            factories.User(fullname="Max Hankins", name="hankins_m"),
            factories.User(fullname="Kathy Tillman", name="tillman_k"),
        ]
        datasets = [
            factories.Dataset(user=users[1]),
            factories.Dataset(user=users[1]),
        ]
        for dataset in datasets:
            dataset["title"] = "Edited title"
            helpers.call_action(
                "package_update", context={"user": users[1]["name"]}, **dataset
            )
        expected_names = [
            u["name"]
            for u in [
                users[0],  # 0 packages created
                users[2],  # 0 packages created
                users[1],  # 2 packages created
            ]
        ]

        got_users = helpers.call_action(
            "user_list", order_by="number_created_packages"
        )
        got_names = [
            u["name"] for u in got_users if u["name"] != default_user["name"]
        ]

        assert got_names == expected_names

    def test_user_list_order_by_edits(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_list", order_by="edits")


@pytest.mark.usefixtures("non_clean_db")
class TestUserShow(object):
    def test_user_show_default_values(self):

        user = factories.User()

        got_user = helpers.call_action("user_show", id=user["id"])

        assert got_user["id"] == user["id"]
        assert got_user["name"] == user["name"]
        assert got_user["fullname"] == user["fullname"]
        assert got_user["display_name"] == user["display_name"]
        assert got_user["created"] == user["created"]
        assert got_user["about"] == user["about"]
        assert got_user["sysadmin"] == user["sysadmin"]
        assert got_user["number_created_packages"] == 0
        assert "password" not in got_user
        assert "reset_key" not in got_user
        assert "apikey" not in got_user
        assert "email" not in got_user
        assert "datasets" not in got_user
        assert "password_hash" not in got_user

    def test_user_show_keep_email(self):

        user = factories.User()

        got_user = helpers.call_action(
            "user_show", context={"keep_email": True}, id=user["id"]
        )

        assert got_user["email"] == user["email"]
        assert "apikey" not in got_user
        assert "password" not in got_user
        assert "reset_key" not in got_user

    def test_user_show_keep_apikey(self):

        user = factories.User()

        got_user = helpers.call_action(
            "user_show", context={"keep_apikey": True}, id=user["id"]
        )

        assert "email" not in got_user
        assert got_user["apikey"] == user["apikey"]
        assert "password" not in got_user
        assert "reset_key" not in got_user

    def test_user_show_normal_user_no_password_hash(self):

        user = factories.User()

        got_user = helpers.call_action(
            "user_show", id=user["id"], include_password_hash=True
        )

        assert "password_hash" not in got_user

    def test_user_show_for_myself(self):

        user = factories.User()

        got_user = helpers.call_action(
            "user_show", context={"user": user["name"]}, id=user["id"]
        )

        assert got_user["email"] == user["email"]
        assert got_user["apikey"] == user["apikey"]
        assert "password" not in got_user
        assert "reset_key" not in got_user

    def test_user_show_sysadmin_values(self):

        user = factories.User()

        sysadmin = factories.User(sysadmin=True)

        got_user = helpers.call_action(
            "user_show", context={"user": sysadmin["name"]}, id=user["id"]
        )

        assert got_user["email"] == user["email"]
        assert got_user["apikey"] == user["apikey"]
        assert "password" not in got_user
        assert "reset_key" not in got_user

    def test_user_show_sysadmin_password_hash(self):

        user = factories.User(password="TestPassword1")

        sysadmin = factories.User(sysadmin=True)

        got_user = helpers.call_action(
            "user_show",
            context={"user": sysadmin["name"]},
            id=user["id"],
            include_password_hash=True,
        )

        assert got_user["email"] == user["email"]
        assert got_user["apikey"] == user["apikey"]
        assert "password_hash" in got_user
        assert "password" not in got_user
        assert "reset_key" not in got_user

    def test_user_show_include_datasets(self):

        user = factories.User()
        dataset = factories.Dataset(user=user)

        got_user = helpers.call_action(
            "user_show", include_datasets=True, id=user["id"]
        )

        assert len(got_user["datasets"]) == 1
        assert got_user["datasets"][0]["name"] == dataset["name"]

    def test_user_show_include_datasets_excludes_draft_and_private(self):

        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        got_user = helpers.call_action(
            "user_show", include_datasets=True, id=user["id"]
        )

        assert len(got_user["datasets"]) == 1
        assert got_user["datasets"][0]["name"] == dataset["name"]
        assert got_user["number_created_packages"] == 1

    def test_user_show_include_datasets_includes_draft_myself(self):
        # a user viewing his own user should see the draft and private datasets

        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user)
        dataset_deleted = factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        got_user = helpers.call_action(
            "user_show",
            context={"user": user["name"]},
            include_datasets=True,
            id=user["id"],
        )

        assert len(got_user["datasets"]) == 3
        datasets_got = set([user_["name"] for user_ in got_user["datasets"]])
        assert dataset_deleted["name"] not in datasets_got
        assert got_user["number_created_packages"] == 3

    def test_user_show_include_datasets_includes_draft_sysadmin(self):
        # sysadmin should see the draft and private datasets

        user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        factories.Dataset(user=user)
        dataset_deleted = factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        got_user = helpers.call_action(
            "user_show",
            context={"user": sysadmin["name"]},
            include_datasets=True,
            id=user["id"],
        )

        assert len(got_user["datasets"]) == 3
        datasets_got = set([user_["name"] for user_ in got_user["datasets"]])
        assert dataset_deleted["name"] not in datasets_got
        assert got_user["number_created_packages"] == 3

    def test_user_show_for_myself_without_passing_id(self):

        user = factories.User()

        got_user = helpers.call_action(
            "user_show", context={"user": user["name"]}
        )

        assert got_user["name"] == user["name"]
        assert got_user["email"] == user["email"]
        assert got_user["apikey"] == user["apikey"]
        assert "password" not in got_user
        assert "reset_key" not in got_user


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestCurrentPackageList(object):
    def test_current_package_list(self):
        """
        Test current_package_list_with_resources with no parameters
        """
        user = factories.User()
        factories.Dataset(user=user)
        factories.Dataset(user=user)
        current_package_list = helpers.call_action(
            "current_package_list_with_resources"
        )
        assert len(current_package_list) == 2

    def test_current_package_list_limit_param(self):
        """
        Test current_package_list_with_resources with limit parameter
        """
        user = factories.User()
        factories.Dataset(user=user)
        dataset2 = factories.Dataset(user=user)
        current_package_list = helpers.call_action(
            "current_package_list_with_resources", limit=1
        )
        assert len(current_package_list) == 1
        assert current_package_list[0]["name"] == dataset2["name"]

    def test_current_package_list_offset_param(self):
        """
        Test current_package_list_with_resources with offset parameter
        """
        user = factories.User()
        dataset1 = factories.Dataset(user=user)
        factories.Dataset(user=user)
        current_package_list = helpers.call_action(
            "current_package_list_with_resources", offset=1
        )
        assert len(current_package_list) == 1
        assert current_package_list[0]["name"] == dataset1["name"]

    def test_current_package_list_private_datasets_anonoymous_user(self):
        """
        Test current_package_list_with_resources with an anonymous user and
        a private dataset
        """
        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(
            user=user, owner_org=org["name"], private=True
        )
        factories.Dataset(user=user)
        current_package_list = helpers.call_action(
            "current_package_list_with_resources", context={}
        )
        assert len(current_package_list) == 1

    def test_current_package_list_private_datasets_sysadmin_user(self):
        """
        Test current_package_list_with_resources with a sysadmin user and a
        private dataset
        """
        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(
            user=user, owner_org=org["name"], private=True
        )
        factories.Dataset(user=user)
        sysadmin = factories.Sysadmin()
        current_package_list = helpers.call_action(
            "current_package_list_with_resources",
            context={"user": sysadmin["name"]},
        )
        assert len(current_package_list) == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestPackageAutocomplete(object):
    def test_package_autocomplete_match_name(self):
        pkg = factories.Dataset(name="warandpeace")
        result = helpers.call_action("package_autocomplete", q="war")
        assert result[0]["name"] == pkg["name"]
        assert result[0]["title"] == pkg["title"]
        assert result[0]["match_field"] == "name"
        assert result[0]["match_displayed"] == pkg["name"]

    def test_package_autocomplete_match_title(self):
        pkg = factories.Dataset(title="A Wonderful Story")
        result = helpers.call_action("package_autocomplete", q="won")
        assert result[0]["name"] == pkg["name"]
        assert result[0]["title"] == pkg["title"]
        assert result[0]["match_field"] == "title"
        assert (
            result[0]["match_displayed"]
            == f"A Wonderful Story ({pkg['name']})"
        )

    def test_package_autocomplete_does_not_return_private_datasets(self):

        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(
            user=user, owner_org=org["name"], title="Some public stuff"
        )
        factories.Dataset(
            user=user,
            owner_org=org["name"],
            private=True,
            title="Some private stuff",
        )

        package_list = helpers.call_action(
            "package_autocomplete", context={"ignore_auth": False}, q="some"
        )
        assert len(package_list) == 1

    def test_package_autocomplete_does_return_private_datasets_from_my_org(
        self,
    ):
        user = factories.User()
        org = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )
        factories.Dataset(
            user=user, owner_org=org["id"], title="Some public stuff"
        )
        factories.Dataset(
            user=user,
            owner_org=org["id"],
            private=True,
            title="Some private stuff",
        )
        package_list = helpers.call_action(
            "package_autocomplete",
            context={"user": user["name"], "ignore_auth": False},
            q="some",
        )
        assert len(package_list) == 2

    def test_package_autocomplete_works_for_the_middle_part_of_title(self):
        factories.Dataset(title="Some public stuff")
        factories.Dataset(title="Some random stuff")

        package_list = helpers.call_action("package_autocomplete", q="bli")
        assert len(package_list) == 1
        package_list = helpers.call_action("package_autocomplete", q="tuf")
        assert len(package_list) == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestPackageSearch(object):
    def test_search(self):
        factories.Dataset(title="Rivers")
        factories.Dataset(title="Lakes")  # decoy

        search_result = helpers.call_action("package_search", q="rivers")

        assert search_result["results"][0]["title"] == "Rivers"
        assert search_result["count"] == 1

    def test_search_fl(self):
        d1 = factories.Dataset(title="Rivers", name="test_ri")
        factories.Dataset(title="Lakes")

        search_result = helpers.call_action(
            "package_search", q="rivers", fl=["title", "name"]
        )
        assert search_result["results"] == [
            {"title": "Rivers", "name": "test_ri"}
        ]

        search_result = helpers.call_action(
            "package_search", q="rivers", fl="title,name"
        )
        assert search_result["results"] == [
            {"title": "Rivers", "name": "test_ri"}
        ]

        search_result = helpers.call_action(
            "package_search", q="rivers", fl=["id"]
        )
        assert search_result["results"] == [{"id": d1["id"]}]

    def test_search_all(self):
        factories.Dataset(title="Rivers")
        factories.Dataset(title="Lakes")

        search_result = helpers.call_action("package_search")  # no q

        assert search_result["count"] == 2

    def test_bad_action_parameter(self):
        with pytest.raises(SearchError):
            helpers.call_action("package_search", weird_param=1)

    def test_bad_solr_parameter(self):
        with pytest.raises(SearchError):
            helpers.call_action("package_search", sort="metadata_modified")
        # SOLR doesn't like that we didn't specify 'asc' or 'desc'
        # SOLR error is 'Missing sort order' or 'Missing_sort_order',
        # depending on the solr version.

    def _create_bulk_datasets(self, name, count):
        from ckan import model

        pkgs = [
            model.Package(name="{}_{}".format(name, i)) for i in range(count)
        ]
        model.Session.add_all(pkgs)
        model.repo.commit_and_remove()

    def test_rows_returned_default(self):
        self._create_bulk_datasets("rows_default", 11)
        results = logic.get_action("package_search")({}, {})
        assert len(results["results"]) == 10  # i.e. 'rows' default value

    @pytest.mark.ckan_config("ckan.search.rows_max", "3")
    def test_rows_returned_limited(self):
        self._create_bulk_datasets("rows_limited", 5)
        results = logic.get_action("package_search")({}, {"rows": "15"})
        assert len(results["results"]) == 3  # i.e. ckan.search.rows_max

    def test_facets(self):
        org = factories.Organization(name="test-org-facet", title="Test Org")
        factories.Dataset(owner_org=org["id"])
        factories.Dataset(owner_org=org["id"])

        data_dict = {"facet.field": ["organization"]}
        search_result = helpers.call_action("package_search", **data_dict)

        assert search_result["count"] == 2
        assert search_result["search_facets"] == {
            "organization": {
                "items": [
                    {
                        "count": 2,
                        "display_name": "Test Org",
                        "name": "test-org-facet",
                    }
                ],
                "title": "organization",
            }
        }

    def test_facet_limit(self):
        group1 = factories.Group(name="test-group-fl1", title="Test Group 1")
        group2 = factories.Group(name="test-group-fl2", title="Test Group 2")
        factories.Dataset(
            groups=[{"name": group1["name"]}, {"name": group2["name"]}]
        )
        factories.Dataset(groups=[{"name": group1["name"]}])
        factories.Dataset()

        data_dict = {"facet.field": ["groups"], "facet.limit": 1}
        search_result = helpers.call_action("package_search", **data_dict)

        assert len(search_result["search_facets"]["groups"]["items"]) == 1
        assert search_result["search_facets"] == {
            "groups": {
                "items": [
                    {
                        "count": 2,
                        "display_name": "Test Group 1",
                        "name": "test-group-fl1",
                    }
                ],
                "title": "groups",
            }
        }

    def test_facet_no_limit(self):
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Dataset(
            groups=[{"name": group1["name"]}, {"name": group2["name"]}]
        )
        factories.Dataset(groups=[{"name": group1["name"]}])
        factories.Dataset()

        data_dict = {"facet.field": ["groups"], "facet.limit": -1}  # no limit
        search_result = helpers.call_action("package_search", **data_dict)

        assert len(search_result["search_facets"]["groups"]["items"]) == 2

    def test_sort(self):
        factories.Dataset(name="test0")
        factories.Dataset(name="test1")
        factories.Dataset(name="test2")

        search_result = helpers.call_action(
            "package_search", sort="metadata_created desc"
        )

        result_names = [result["name"] for result in search_result["results"]]
        assert result_names == ["test2", "test1", "test0"]

    @pytest.mark.ckan_config(
        "ckan.search.default_package_sort", "metadata_created asc"
    )
    def test_sort_default_from_config(self):
        factories.Dataset(name="test0")
        factories.Dataset(name="test1")
        factories.Dataset(name="test2")

        search_result = helpers.call_action("package_search")

        result_names = [result["name"] for result in search_result["results"]]
        assert result_names == ["test0", "test1", "test2"]

    def test_package_search_on_resource_name(self):
        """
        package_search() should allow searching on resource name field.
        """
        resource_name = "resource_abc"
        factories.Resource(name=resource_name)

        search_result = helpers.call_action("package_search", q="resource_abc")
        assert (
            search_result["results"][0]["resources"][0]["name"]
            == resource_name
        )

    def test_package_search_excludes_private_and_drafts(self):
        """
        package_search() with no options should not return private and draft
        datasets.
        """
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        results = helpers.call_action("package_search")["results"]

        assert len(results) == 1
        assert results[0]["name"] == dataset["name"]

    def test_package_search_with_fq_excludes_private(self):
        """
        package_search() with fq capacity:private should not return private
        and draft datasets.
        """
        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        fq = "capacity:private"
        results = helpers.call_action("package_search", fq=fq)["results"]

        assert len(results) == 0

    def test_package_search_with_fq_excludes_drafts(self):
        """
        A sysadmin user can't use fq drafts to get draft datasets. Nothing is
        returned.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        factories.Dataset(user=user, state="draft", name="draft-dataset")
        factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "state:draft"
        results = helpers.call_action("package_search", fq=fq)["results"]

        assert len(results) == 0

    def test_package_search_with_include_drafts_option_excludes_drafts_for_anon_user(
        self,
    ):
        """
        An anon user can't user include_drafts to get draft datasets.
        """
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        draft_dataset = factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        results = logic.get_action("package_search")(
            {"user": ""}, {"include_drafts": True}
        )["results"]

        assert len(results) == 1
        assert results[0]["name"] != draft_dataset["name"]
        assert results[0]["name"] == dataset["name"]

    def test_package_search_with_include_drafts_option_includes_drafts_for_sysadmin(
        self,
    ):
        """
        A sysadmin can use the include_drafts option to get draft datasets for
        all users.
        """
        user = factories.User()
        other_user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        draft_dataset = factories.Dataset(user=user, state="draft")
        other_draft_dataset = factories.Dataset(user=other_user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        results = logic.get_action("package_search")(
            {"user": sysadmin["name"]}, {"include_drafts": True}
        )["results"]

        assert len(results) == 3
        names = [r["name"] for r in results]
        assert draft_dataset["name"] in names
        assert other_draft_dataset["name"] in names
        assert dataset["name"] in names

    def test_package_search_with_include_drafts_false_option_doesnot_include_drafts_for_sysadmin(
        self,
    ):
        """
        A sysadmin with include_drafts option set to `False` will not get
        drafts returned in results.
        """
        user = factories.User()
        other_user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        draft_dataset = factories.Dataset(user=user, state="draft")
        other_draft_dataset = factories.Dataset(user=other_user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        results = logic.get_action("package_search")(
            {"user": sysadmin["name"]}, {"include_drafts": False}
        )["results"]

        assert len(results) == 1
        names = [r["name"] for r in results]
        assert draft_dataset["name"] not in names
        assert other_draft_dataset["name"] not in names
        assert dataset["name"] in names

    def test_package_search_with_include_drafts_option_includes_drafts_for_user(
        self,
    ):
        """
        The include_drafts option will include draft datasets for the
        authorized user, but not drafts for other users.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(
            user=other_user, name="other-dataset"
        )
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        draft_dataset = factories.Dataset(
            user=user, state="draft", name="draft-dataset"
        )
        other_draft_dataset = factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"include_drafts": True}
        )["results"]

        assert len(results) == 3
        names = [r["name"] for r in results]
        assert draft_dataset["name"] in names
        assert other_draft_dataset["name"] not in names
        assert dataset["name"] in names
        assert other_dataset["name"] in names

    def test_package_search_with_fq_for_create_user_id_will_include_datasets_for_other_users(
        self,
    ):
        """
        A normal user can use the fq creator_user_id to get active datasets
        (but not draft) for another user.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(
            user=other_user, name="other-dataset"
        )
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        draft_dataset = factories.Dataset(
            user=user, state="draft", name="draft-dataset"
        )
        other_draft_dataset = factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "creator_user_id:{0}".format(other_user["id"])
        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"fq": fq}
        )["results"]

        assert len(results) == 1
        names = [r["name"] for r in results]
        assert draft_dataset["name"] not in names
        assert other_draft_dataset["name"] not in names
        assert dataset["name"] not in names
        assert other_dataset["name"] in names

    def test_package_search_with_fq_for_create_user_id_will_not_include_drafts_for_other_users(
        self,
    ):
        """
        A normal user can't use fq creator_user_id and drafts to get draft
        datasets for another user.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        factories.Dataset(user=user, state="draft", name="draft-dataset")
        factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "(creator_user_id:{0} AND +state:draft)".format(other_user["id"])
        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"fq": fq, "include_drafts": True}
        )["results"]

        assert len(results) == 0

    def test_package_search_with_fq_for_creator_user_id_and_drafts_and_include_drafts_option_will_not_include_drafts_for_other_user(
        self,
    ):
        """
        A normal user can't use fq creator_user_id and drafts and the
        include_drafts option to get draft datasets for another user.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        factories.Dataset(user=user, state="draft", name="draft-dataset")
        factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "(creator_user_id:{0} AND +state:draft)".format(other_user["id"])
        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"fq": fq, "include_drafts": True}
        )["results"]

        assert len(results) == 0

    def test_package_search_with_fq_for_creator_user_id_and_include_drafts_option_will_not_include_drafts_for_other_user(
        self,
    ):
        """
        A normal user can't use fq creator_user_id and the include_drafts
        option to get draft datasets for another user.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(
            user=other_user, name="other-dataset"
        )
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        factories.Dataset(user=user, state="draft", name="draft-dataset")
        other_draft_dataset = factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "creator_user_id:{0}".format(other_user["id"])
        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"fq": fq, "include_drafts": True}
        )["results"]

        names = [r["name"] for r in results]
        assert len(results) == 1
        assert other_dataset["name"] in names
        assert other_draft_dataset["name"] not in names

    def test_package_search_with_fq_for_create_user_id_will_include_drafts_for_other_users_for_sysadmin(
        self,
    ):
        """
        Sysadmins can use fq to get draft datasets for another user.
        """
        user = factories.User()
        sysadmin = factories.Sysadmin()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        draft_dataset = factories.Dataset(
            user=user, state="draft", name="draft-dataset"
        )
        factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "(creator_user_id:{0} AND +state:draft)".format(user["id"])
        results = logic.get_action("package_search")(
            {"user": sysadmin["name"]}, {"fq": fq}
        )["results"]

        names = [r["name"] for r in results]
        assert len(results) == 1
        assert dataset["name"] not in names
        assert draft_dataset["name"] in names

    def test_package_search_private_with_include_private(self):
        """
        package_search() can return private datasets when
        `include_private=True`
        """
        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        private_dataset = factories.Dataset(
            user=user, private=True, owner_org=org["name"]
        )

        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"include_private": True}
        )["results"]

        assert [r["name"] for r in results] == [private_dataset["name"]]

    @pytest.mark.parametrize("remove_deleted_setting", [True, False])
    def test_package_search_private_with_include_private_wont_show_other_orgs_private(
        self, remove_deleted_setting
    ):
        with helpers.changed_config("ckan.search.remove_deleted_packages", remove_deleted_setting):
            user = factories.User()
            user2 = factories.User()
            factories.Organization(user=user)
            org2 = factories.Organization(user=user2)
            # create a deleted dataset if we expect them to be indexed
            factories.Dataset(
                user=user2,
                private=True,
                owner_org=org2["name"],
                state="active" if remove_deleted_setting else "deleted",
            )

            # include deleted datasets if we expect them to be indexed
            results = logic.get_action("package_search")(
                {"user": user["name"]},
                {"include_private": True, "include_deleted": not remove_deleted_setting},
            )["results"]

            assert [r["name"] for r in results] == []

    @pytest.mark.parametrize("remove_deleted_setting", [True, False])
    def test_package_search_private_with_include_private_syadmin(self, remove_deleted_setting):
        with helpers.changed_config("ckan.search.remove_deleted_packages", remove_deleted_setting):
            user = factories.User()
            sysadmin = factories.Sysadmin()
            org = factories.Organization(user=user)
            # create a deleted dataset if we expect them to be indexed
            private_dataset = factories.Dataset(
                user=user,
                private=True,
                owner_org=org["name"],
                state="active" if remove_deleted_setting else "deleted",
            )

            # include deleted datasets if we expect them to be indexed
            results = logic.get_action("package_search")(
                {"user": sysadmin["name"]},
                {"include_private": True, "include_deleted": not remove_deleted_setting}
            )["results"]

            assert [r["name"] for r in results] == [private_dataset["name"]]

    def test_package_works_without_user_in_context(self):
        """
        package_search() should work even if user isn't in the context (e.g.
        ckanext-showcase tests.
        """
        logic.get_action("package_search")({}, dict(q="anything"))

    def test_local_parameters_not_supported(self):
        with pytest.raises(SearchError):
            helpers.call_action(
                "package_search", q='{!child of="content_type:parentDoc"}'
            )


@pytest.mark.ckan_config("ckan.plugins", "example_idatasetform")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestPackageAutocompleteWithDatasetForm(object):
    def test_custom_schema_returned(self):
        dataset1 = factories.Dataset(custom_text="foo")

        query = helpers.call_action(
            "package_search", q="id:{0}".format(dataset1["id"])
        )

        assert query["results"][0]["id"] == dataset1["id"]
        assert query["results"][0]["custom_text"] == "foo"

    def test_custom_schema_not_returned(self):
        dataset1 = factories.Dataset(custom_text="foo")

        query = helpers.call_action(
            "package_search",
            q="id:{0}".format(dataset1["id"]),
            use_default_schema=True,
        )

        assert query["results"][0]["id"] == dataset1["id"]
        assert "custom_text" not in query["results"][0]
        assert query["results"][0]["extras"][0]["key"] == "custom_text"
        assert query["results"][0]["extras"][0]["value"] == "foo"


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestUserAutocomplete(object):
    def test_autocomplete(self):
        factories.Sysadmin(name="autocompletesysadmin")
        factories.User(name="autocompleteuser")
        result = helpers.call_action("user_autocomplete", q="sysadmin")
        assert len(result) == 1
        user = result.pop()
        assert set(user.keys()) == set(["id", "name", "fullname"])
        assert user["name"] == "autocompletesysadmin"

    def test_autocomplete_multiple(self):
        factories.Sysadmin(name="autocompletesysadmin")
        factories.User(name="autocompleteuser")
        result = helpers.call_action("user_autocomplete", q="compl")
        assert len(result) == 2

    def test_autocomplete_limit(self):
        factories.Sysadmin(name="autocompletesysadmin")
        factories.User(name="autocompleteuser")
        result = helpers.call_action("user_autocomplete", q="compl", limit=1)
        assert len(result) == 1


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestFormatAutocomplete:
    def test_missing_param(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("format_autocomplete")

    def test_autocomplete(self):
        result = helpers.call_action("format_autocomplete", q="cs")
        assert result == []
        factories.Resource(format="CSV")
        result = helpers.call_action("format_autocomplete", q="cs")
        assert result == ["csv"]


@pytest.mark.usefixtures("clean_db")
class TestBadLimitQueryParameters(object):
    """test class for #1258 non-int query parameters cause 500 errors

    Test that validation errors are raised when calling actions with
    bad parameters.
    """

    def test_package_search_facet_field_is_json(self):
        kwargs = {"facet.field": "notjson"}
        with pytest.raises(logic.ValidationError):
            helpers.call_action("package_search", **kwargs)


@pytest.mark.usefixtures("clean_db")
class TestOrganizationListForUser(object):
    """Functional tests for the organization_list_for_user() action function."""

    def test_when_user_is_not_a_member_of_any_organizations(self):
        """
        When the user isn't a member of any organizations (in any capacity)
        organization_list_for_user() should return an empty list.
        """
        user = factories.User()
        context = {"user": user["name"]}

        # Create an organization so we can test that it does not get returned.
        factories.Organization()

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert organizations == []

    def test_when_user_is_an_admin_of_one_organization(self):
        """
        When the user is an admin of one organization
        organization_list_for_user() should return a list of just that one
        organization.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        # Create a second organization just so we can test that it does not get
        # returned.
        factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="admin",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert len(organizations) == 1
        assert organizations[0]["id"] == organization["id"]

    def test_when_user_is_an_admin_of_three_organizations(self):
        """
        When the user is an admin of three organizations
        organization_list_for_user() should return a list of all three
        organizations.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization_1 = factories.Organization()
        organization_2 = factories.Organization()
        organization_3 = factories.Organization()

        # Create a second organization just so we can test that it does not get
        # returned.
        factories.Organization()

        # Make the user an admin of all three organizations:
        for organization in (organization_1, organization_2, organization_3):
            helpers.call_action(
                "member_create",
                id=organization["id"],
                object=user["id"],
                object_type="user",
                capacity="admin",
            )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert len(organizations) == 3
        ids = [organization["id"] for organization in organizations]
        for organization in (organization_1, organization_2, organization_3):
            assert organization["id"] in ids

    def test_when_permissions_extend_to_sub_organizations(self):
        """

        When the user is an admin of one organization
        organization_list_for_user() should return a list of just that one
        organization.

        """
        user = factories.User()
        context = {"user": user["name"]}
        user["capacity"] = "admin"
        top_organization = factories.Organization(users=[user])
        middle_organization = factories.Organization(users=[user])
        bottom_organization = factories.Organization()

        # Create another organization just so we can test that it does not get
        # returned.
        factories.Organization()

        helpers.call_action(
            "member_create",
            id=bottom_organization["id"],
            object=middle_organization["id"],
            object_type="group",
            capacity="parent",
        )
        helpers.call_action(
            "member_create",
            id=middle_organization["id"],
            object=top_organization["id"],
            object_type="group",
            capacity="parent",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert len(organizations) == 3
        org_ids = set(org["id"] for org in organizations)
        assert bottom_organization["id"] in org_ids

    def test_does_return_members(self):
        """
        By default organization_list_for_user() should return organizations
        that the user is just a member (not an admin) of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="member",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_does_return_editors(self):
        """
        By default organization_list_for_user() should return organizations
        that the user is just an editor (not an admin) of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="editor",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_editor_permission(self):
        """
        organization_list_for_user() should return organizations that the user
        is an editor of if passed a permission that belongs to the editor role.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="editor",
        )

        organizations = helpers.call_action(
            "organization_list_for_user",
            permission="create_dataset",
            context=context,
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_member_permission(self):
        """
        organization_list_for_user() should return organizations that the user
        is a member of if passed a permission that belongs to the member role.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="member",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", permission="read", context=context
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_invalid_permission(self):
        """
        organization_list_for_user() should return an empty list if passed a
        non-existent or invalid permission.

        Note that we test this with a user who is an editor of one organization.
        If the user was an admin of the organization then it would return that
        organization - admins have all permissions, including permissions that
        don't exist.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()
        factories.Organization()
        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="editor",
        )

        for permission in ("", " ", "foo", 27.3, 5, True, False, None):
            organizations = helpers.call_action(
                "organization_list_for_user",
                permission=permission,
                context=context,
            )

        assert organizations == []

    def test_that_it_does_not_return_groups(self):
        """
        organization_list_for_user() should not return groups that the user is
        a member, editor or admin of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        group_1 = factories.Group()
        group_2 = factories.Group()
        group_3 = factories.Group()
        helpers.call_action(
            "member_create",
            id=group_1["id"],
            object=user["id"],
            object_type="user",
            capacity="member",
        )
        helpers.call_action(
            "member_create",
            id=group_2["id"],
            object=user["id"],
            object_type="user",
            capacity="editor",
        )
        helpers.call_action(
            "member_create",
            id=group_3["id"],
            object=user["id"],
            object_type="user",
            capacity="admin",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert organizations == []

    def test_that_it_does_not_return_previous_memberships(self):
        """
        organization_list_for_user() should return organizations that the user
        was previously an admin of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        # Make the user an admin of the organization.
        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="admin",
        )

        # Remove the user from the organization.
        helpers.call_action(
            "member_delete",
            id=organization["id"],
            object=user["id"],
            object_type="user",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert organizations == []

    def test_when_user_is_sysadmin(self):
        """
        When the user is a sysadmin organization_list_for_user() should just
        return all organizations, even if the user is not a member of them.
        """
        user = factories.Sysadmin()
        context = {"user": user["name"]}
        organization = factories.Organization()

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_that_it_does_not_return_deleted_organizations(self):
        """
        organization_list_for_user() should not return deleted organizations
        that the user was an admin of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        # Make the user an admin of the organization.
        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="admin",
        )

        # Delete the organization.
        helpers.call_action(
            "organization_delete", id=organization["id"], context=context
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert organizations == []

    def test_with_no_authorized_user(self):
        """
        organization_list_for_user() should return an empty list if there's no
        authorized user. Users who aren't logged-in don't have any permissions.
        """
        # Create an organization so we can test that it doesn't get returned.
        factories.Organization()

        organizations = helpers.call_action("organization_list_for_user")

        assert organizations == []

    def test_organization_list_for_user_returns_all_roles(self):

        user1 = factories.User()
        user2 = factories.User()
        user3 = factories.User()

        org1 = factories.Organization(
            users=[
                {"name": user1["name"], "capacity": "admin"},
                {"name": user2["name"], "capacity": "editor"},
            ]
        )
        org2 = factories.Organization(
            users=[
                {"name": user1["name"], "capacity": "member"},
                {"name": user2["name"], "capacity": "member"},
            ]
        )
        org3 = factories.Organization(
            users=[{"name": user1["name"], "capacity": "editor"}]
        )

        org_list_for_user1 = helpers.call_action(
            "organization_list_for_user", id=user1["id"]
        )

        assert sorted([org["id"] for org in org_list_for_user1]) == sorted(
            [org1["id"], org2["id"], org3["id"]]
        )

        org_list_for_user2 = helpers.call_action(
            "organization_list_for_user", id=user2["id"]
        )

        assert sorted([org["id"] for org in org_list_for_user2]) == sorted(
            [org1["id"], org2["id"]]
        )

        org_list_for_user3 = helpers.call_action(
            "organization_list_for_user", id=user3["id"]
        )

        assert org_list_for_user3 == []


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestShowResourceView(object):
    def test_resource_view_show(self):

        resource = factories.Resource()
        resource_view = {
            "resource_id": resource["id"],
            "view_type": "image_view",
            "title": "View",
            "description": "A nice view",
            "image_url": "url",
        }

        new_view = helpers.call_action("resource_view_create", **resource_view)

        result = helpers.call_action("resource_view_show", id=new_view["id"])

        result.pop("id")
        result.pop("package_id")

        assert result == resource_view

    def test_resource_view_show_id_missing(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_show")

    def test_resource_view_show_id_not_found(self):

        with pytest.raises(logic.NotFound):
            helpers.call_action("resource_view_show", id="does_not_exist")


class TestGetHelpShow(object):
    def test_help_show_basic(self):

        function_name = "package_search"

        result = helpers.call_action("help_show", name=function_name)

        function = logic.get_action(function_name)

        assert result == function.__doc__

    def test_help_show_no_docstring(self):

        function_name = "package_search"

        function = logic.get_action(function_name)

        actual_docstring = function.__doc__

        function.__doc__ = None

        result = helpers.call_action("help_show", name=function_name)

        function.__doc__ = actual_docstring

        assert result is None

    def test_help_show_not_found(self):

        function_name = "unknown_action"

        with pytest.raises(logic.NotFound):
            helpers.call_action("help_show", name=function_name)


@pytest.mark.usefixtures("non_clean_db")
class TestConfigOptionShow(object):
    @pytest.mark.ckan_config("ckan.site_title", "My Test CKAN")
    def test_config_option_show_in_config_not_in_db(self):
        """config_option_show returns value from config when value on in
        system_info table."""

        title = helpers.call_action(
            "config_option_show", key="ckan.site_title"
        )
        assert title == "My Test CKAN"

    @pytest.mark.ckan_config("ckan.site_title", "My Test CKAN")
    def test_config_option_show_in_config_and_in_db(self):
        """config_option_show returns value from db when value is in both
        config and system_info table."""

        params = {"ckan.site_title": "Test site title"}
        helpers.call_action("config_option_update", **params)

        title = helpers.call_action(
            "config_option_show", key="ckan.site_title"
        )
        assert title == "Test site title"

    @pytest.mark.ckan_config("ckan.not.editable", "My non editable option")
    def test_config_option_show_not_whitelisted_key(self):
        """config_option_show raises exception if key is not a whitelisted
        config option."""

        with pytest.raises(logic.ValidationError):
            helpers.call_action("config_option_show", key="ckan.not.editable")


class TestConfigOptionList(object):
    def test_config_option_list(self):
        """config_option_list returns whitelisted config option keys"""

        keys = helpers.call_action("config_option_list")
        schema_keys = list(schema.update_configuration_schema().keys())

        assert keys == schema_keys


def remove_pseudo_users(user_list):
    pseudo_users = set(("logged_in", "visitor"))
    user_list[:] = [
        user for user in user_list if user["name"] not in pseudo_users
    ]


@pytest.mark.usefixtures("non_clean_db")
class TestTagShow(object):
    def test_tag_show_for_free_tag(self):
        tag = factories.Tag.stub().name
        dataset = factories.Dataset(tags=[{"name": tag}])
        tag_in_dataset = dataset["tags"][0]

        tag_shown = helpers.call_action("tag_show", id=tag)

        assert tag_shown["name"] == tag
        assert tag_shown["display_name"] == tag
        assert tag_shown["id"] == tag_in_dataset["id"]
        assert tag_shown["vocabulary_id"] is None
        assert "packages" not in tag_shown

    @pytest.mark.usefixtures("clean_index")
    def test_tag_show_with_datasets(self):
        tag = factories.Tag.stub().name
        dataset = factories.Dataset(tags=[{"name": tag}])

        tag_shown = helpers.call_action(
            "tag_show", id=tag, include_datasets=True
        )

        assert [d["name"] for d in tag_shown["packages"]] == [dataset["name"]]

    def test_tag_show_not_found(self):
        with pytest.raises(logic.NotFound):
            helpers.call_action("tag_show", id=factories.Tag.stub().name)

    @pytest.mark.usefixtures("clean_db")
    def test_tag_show_for_flexible_tag(self):
        # A 'flexible' tag is one with spaces, some punctuation
        # and foreign characters in its name
        dataset = factories.Dataset(tags=[{"name": "Flexible. \u30a1"}])

        tag_shown = helpers.call_action(
            "tag_show", id="Flexible. \u30a1", include_datasets=True
        )

        assert tag_shown["name"] == "Flexible. \u30a1"
        assert tag_shown["display_name"] == "Flexible. \u30a1"
        assert [d["name"] for d in tag_shown["packages"]] == [dataset["name"]]

    def test_tag_show_for_vocab_tag(self):
        tag = factories.Tag.stub().name
        vocab = factories.Vocabulary(tags=[dict(name=tag)])
        dataset = factories.Dataset(tags=vocab["tags"])
        tag_in_dataset = dataset["tags"][0]

        tag_shown = helpers.call_action(
            "tag_show",
            id=tag,
            vocabulary_id=vocab["id"],
            include_datasets=True,
        )

        assert tag_shown["name"] == tag
        assert tag_shown["display_name"] == tag
        assert tag_shown["id"] == tag_in_dataset["id"]
        assert tag_shown["vocabulary_id"] == vocab["id"]
        assert [d["name"] for d in tag_shown["packages"]] == [dataset["name"]]


@pytest.mark.usefixtures("clean_db")
class TestTagList(object):
    def test_tag_list(self):
        tag = factories.Tag.stub().name
        tag2 = factories.Tag.stub().name
        factories.Dataset(tags=[{"name": tag}, {"name": tag2}])
        factories.Dataset(tags=[{"name": tag2}])

        tag_list = helpers.call_action("tag_list")

        assert set(tag_list) == set((tag, tag2))

    def test_tag_list_all_fields(self):
        factories.Dataset(tags=[{"name": "acid-rain"}])

        tag_list = helpers.call_action("tag_list", all_fields=True)

        assert tag_list[0]["name"] == "acid-rain"
        assert tag_list[0]["display_name"] == "acid-rain"
        assert "packages" not in tag_list

    def test_tag_list_with_flexible_tag(self):
        # A 'flexible' tag is one with spaces, punctuation (apart from commas)
        # and foreign characters in its name
        flexible_tag = "Flexible. \u30a1"
        factories.Dataset(tags=[{"name": flexible_tag}])

        tag_list = helpers.call_action("tag_list", all_fields=True)

        assert tag_list[0]["name"] == flexible_tag

    def test_tag_list_with_vocab(self):
        vocab = factories.Vocabulary(
            tags=[dict(name="acid-rain"), dict(name="pollution")]
        )

        tag_list = helpers.call_action("tag_list", vocabulary_id=vocab["id"])

        assert set(tag_list) == set(("acid-rain", "pollution"))

    def test_tag_list_vocab_not_found(self):
        with pytest.raises(logic.NotFound):
            helpers.call_action("tag_list", vocabulary_id="does-not-exist")


@pytest.mark.usefixtures("clean_db")
class TestMembersList(object):
    def test_dataset_delete_marks_membership_of_group_as_deleted(self):
        sysadmin = factories.Sysadmin()
        group = factories.Group()
        dataset = factories.Dataset(groups=[{"name": group["name"]}])
        context = {"user": sysadmin["name"]}

        group_members = helpers.call_action(
            "member_list", context, id=group["id"], object_type="package"
        )

        assert len(group_members) == 1
        assert group_members[0][0] == dataset["id"]
        assert group_members[0][1] == "package"

        helpers.call_action("package_delete", context, id=dataset["id"])

        group_members = helpers.call_action(
            "member_list", context, id=group["id"], object_type="package"
        )

        assert len(group_members) == 0

    def test_dataset_delete_marks_membership_of_org_as_deleted(self):
        sysadmin = factories.Sysadmin()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        context = {"user": sysadmin["name"]}

        org_members = helpers.call_action(
            "member_list", context, id=org["id"], object_type="package"
        )

        assert len(org_members) == 1
        assert org_members[0][0] == dataset["id"]
        assert org_members[0][1] == "package"

        helpers.call_action("package_delete", context, id=dataset["id"])

        org_members = helpers.call_action(
            "member_list", context, id=org["id"], object_type="package"
        )

        assert len(org_members) == 0

    def test_user_delete_marks_membership_of_group_as_deleted(self):
        sysadmin = factories.Sysadmin()
        group = factories.Group()
        user = factories.User()
        context = {"user": sysadmin["name"]}

        member_dict = {
            "username": user["id"],
            "id": group["id"],
            "role": "member",
        }
        helpers.call_action("group_member_create", context, **member_dict)

        group_members = helpers.call_action(
            "member_list",
            context,
            id=group["id"],
            object_type="user",
            capacity="member",
        )

        assert len(group_members) == 1
        assert group_members[0][0] == user["id"]
        assert group_members[0][1] == "user"

        helpers.call_action("user_delete", context, id=user["id"])

        group_members = helpers.call_action(
            "member_list",
            context,
            id=group["id"],
            object_type="user",
            capacity="member",
        )

        assert len(group_members) == 0

    def test_user_delete_marks_membership_of_org_as_deleted(self):
        sysadmin = factories.Sysadmin()
        org = factories.Organization()
        user = factories.User()
        context = {"user": sysadmin["name"]}

        member_dict = {
            "username": user["id"],
            "id": org["id"],
            "role": "member",
        }
        helpers.call_action(
            "organization_member_create", context, **member_dict
        )

        org_members = helpers.call_action(
            "member_list",
            context,
            id=org["id"],
            object_type="user",
            capacity="member",
        )

        assert len(org_members) == 1
        assert org_members[0][0] == user["id"]
        assert org_members[0][1] == "user"

        helpers.call_action("user_delete", context, id=user["id"])

        org_members = helpers.call_action(
            "member_list",
            context,
            id=org["id"],
            object_type="user",
            capacity="member",
        )

        assert len(org_members) == 0


@pytest.mark.usefixtures("non_clean_db")
class TestFollow(object):
    def test_followee_list(self):

        group1 = factories.Group(title="Finance")
        group2 = factories.Group(title="Environment")
        factories.Group(title="Education")

        user = factories.User()

        context = {"user": user["name"]}

        helpers.call_action("follow_group", context, id=group1["id"])
        helpers.call_action("follow_group", context, id=group2["id"])

        followee_list = helpers.call_action(
            "followee_list", context, id=user["name"]
        )

        assert len(followee_list) == 2
        assert sorted([f["display_name"] for f in followee_list]) == [
            "Environment",
            "Finance",
        ]

    def test_followee_list_with_q(self):

        group1 = factories.Group(title="Finance")
        group2 = factories.Group(title="Environment")
        factories.Group(title="Education")

        user = factories.User()

        context = {"user": user["name"]}

        helpers.call_action("follow_group", context, id=group1["id"])
        helpers.call_action("follow_group", context, id=group2["id"])

        followee_list = helpers.call_action(
            "followee_list", context, id=user["name"], q="E"
        )

        assert len(followee_list) == 1
        assert followee_list[0]["display_name"] == "Environment"

    def test_followee_count_for_org_or_group(self):
        group = factories.Group(title="Finance")
        group2 = factories.Group(title="Environment")
        org = factories.Organization(title="Acme")

        user = factories.User()

        context = {"user": user["name"]}

        helpers.call_action("follow_group", context, id=group["id"])
        helpers.call_action("follow_group", context, id=group2["id"])
        helpers.call_action("follow_group", context, id=org["id"])

        group_followee_count = helpers.call_action(
            "group_followee_count", context, id=user["name"]
        )

        organization_followee_count = helpers.call_action(
            "organization_followee_count", context, id=user["name"]
        )

        assert group_followee_count == 2
        assert organization_followee_count == 1


class TestStatusShow(object):
    @pytest.mark.ckan_config("ckan.plugins", "stats")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_status_show(self):

        status = helpers.call_action("status_show")

        assert status["ckan_version"] == __version__
        assert status["site_url"] == "http://test.ckan.net"
        assert status["site_title"] == "CKAN"
        assert status["site_description"] == ""
        assert status["locale_default"] == "en"

        assert isinstance(status["extensions"], list)
        assert status["extensions"] == ["stats"]

    @pytest.mark.ckan_config("ckan.plugins", "stats")
    @pytest.mark.ckan_config('ckan.hide_version', True)
    @pytest.mark.usefixtures("with_plugins")
    def test_status_show_hiding_version(self):

        status = helpers.call_action("status_show")

        assert "ckan_version" not in status, "Should have skipped CKAN version"
        assert status["site_url"] == "http://test.ckan.net"
        assert status["site_title"] == "CKAN"
        assert status["site_description"] == ""
        assert status["locale_default"] == "en"

        assert isinstance(status["extensions"], list)
        assert status["extensions"] == ["stats"]

    @pytest.mark.ckan_config("ckan.plugins", "stats")
    @pytest.mark.ckan_config('ckan.hide_version', True)
    @pytest.mark.usefixtures("with_plugins")
    def test_status_show_version_to_sysadmins(self):
        sysadmin = factories.Sysadmin()
        status = helpers.call_action("status_show", context={"user": sysadmin["name"]})

        assert status["ckan_version"] == __version__
        assert status["site_url"] == "http://test.ckan.net"
        assert status["site_title"] == "CKAN"
        assert status["site_description"] == ""
        assert status["locale_default"] == "en"

        assert isinstance(status["extensions"], list)
        assert status["extensions"] == ["stats"]


class TestJobList(helpers.FunctionalRQTestBase):
    def test_all_queues(self):
        """
        Test getting jobs from all queues.
        """
        job1 = self.enqueue()
        job2 = self.enqueue()
        job3 = self.enqueue(queue="my_queue")
        jobs = helpers.call_action("job_list")
        assert len(jobs) == 3
        assert {job["id"] for job in jobs} == {job1.id, job2.id, job3.id}

    def test_specific_queues(self):
        """
        Test getting jobs from specific queues.
        """
        self.enqueue()
        job2 = self.enqueue(queue="q2")
        job3 = self.enqueue(queue="q3")
        job4 = self.enqueue(queue="q3")
        jobs = helpers.call_action("job_list", queues=["q2"])
        assert len(jobs) == 1
        assert jobs[0]["id"] == job2.id
        jobs = helpers.call_action("job_list", queues=["q2", "q3"])
        assert len(jobs) == 3
        assert {job["id"] for job in jobs} == {job2.id, job3.id, job4.id}


class TestJobShow(helpers.FunctionalRQTestBase):
    def test_existing_job(self):
        """
        Test showing an existing job.
        """
        job = self.enqueue(queue="my_queue", title="Title")
        d = helpers.call_action("job_show", id=job.id)
        assert d["id"] == job.id
        assert d["title"] == "Title"
        assert d["queue"] == "my_queue"
        assert _seconds_since_timestamp(d["created"], "%Y-%m-%dT%H:%M:%S") < 10

    def test_not_existing_job(self):
        """
        Test showing a not existing job.
        """
        with pytest.raises(logic.NotFound):
            helpers.call_action("job_show", id="does-not-exist")


def _seconds_since_timestamp(timestamp, format_):
    dt = datetime.datetime.strptime(timestamp, format_)
    now = datetime.datetime.utcnow()
    assert now > dt  # we assume timestamp is not in the future
    return (now - dt).total_seconds()


@pytest.mark.usefixtures("non_clean_db")
class TestApiToken(object):
    @pytest.mark.parametrize("num_tokens", [0, 1, 2, 5])
    def test_token_list(self, num_tokens):
        from ckan.lib.api_token import decode

        user = factories.User()
        ids = []
        for _ in range(num_tokens):
            data = helpers.call_action(
                "api_token_create",
                context={"model": model, "user": user["name"]},
                user=user["name"],
                name="token-name",
            )
            token = data["token"]
            ids.append(decode(token)["jti"])

        tokens = helpers.call_action(
            "api_token_list",
            context={"model": model, "user": user["name"]},
            user_id=user["name"],
        )
        assert sorted([t["id"] for t in tokens]) == sorted(ids)

        # Param "user" works for backwards compatibility
        tokens = helpers.call_action(
            "api_token_list",
            context={"model": model, "user": user["name"]},
            user=user["name"],
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", False)
def test_package_collaborator_list_when_config_disabled():

    dataset = factories.Dataset()

    with pytest.raises(logic.ValidationError):
        helpers.call_action("package_collaborator_list", id=dataset["id"])


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberList(object):
    def test_list(self):

        dataset = factories.Dataset()
        user1 = factories.User()
        capacity1 = "editor"
        user2 = factories.User()
        capacity2 = "member"

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user1["id"],
            capacity=capacity1,
        )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user2["id"],
            capacity=capacity2,
        )

        members = helpers.call_action(
            "package_collaborator_list", id=dataset["id"]
        )

        assert len(members) == 2

        assert members[0]["package_id"] == dataset["id"]
        assert members[0]["user_id"] == user1["id"]
        assert members[0]["capacity"] == capacity1

        assert members[1]["package_id"] == dataset["id"]
        assert members[1]["user_id"] == user2["id"]
        assert members[1]["capacity"] == capacity2

    def test_list_with_capacity(self):

        dataset = factories.Dataset()
        user1 = factories.User()
        capacity1 = "editor"
        user2 = factories.User()
        capacity2 = "member"

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user1["id"],
            capacity=capacity1,
        )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user2["id"],
            capacity=capacity2,
        )

        members = helpers.call_action(
            "package_collaborator_list", id=dataset["id"], capacity="member"
        )

        assert len(members) == 1

        assert members[0]["package_id"] == dataset["id"]
        assert members[0]["user_id"] == user2["id"]
        assert members[0]["capacity"] == capacity2

    def test_list_dataset_not_found(self):

        with pytest.raises(logic.NotFound):
            helpers.call_action("package_collaborator_list", id="xxx")

    def test_list_wrong_capacity(self):
        dataset = factories.Dataset()
        user = factories.User()
        capacity = "unknown"

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "package_collaborator_list",
                id=dataset["id"],
                user_id=user["id"],
                capacity=capacity,
            )

    def test_list_for_user(self):

        dataset1 = factories.Dataset()
        dataset2 = factories.Dataset()
        user = factories.User()
        capacity1 = "editor"
        capacity2 = "member"

        helpers.call_action(
            "package_collaborator_create",
            id=dataset1["id"],
            user_id=user["id"],
            capacity=capacity1,
        )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset2["id"],
            user_id=user["id"],
            capacity=capacity2,
        )

        datasets = helpers.call_action(
            "package_collaborator_list_for_user", id=user["id"]
        )

        assert len(datasets) == 2

        assert datasets[0]["package_id"] == dataset1["id"]
        assert datasets[0]["capacity"] == capacity1

        assert datasets[1]["package_id"] == dataset2["id"]
        assert datasets[1]["capacity"] == capacity2

    def test_list_for_user_with_capacity(self):

        dataset1 = factories.Dataset()
        dataset2 = factories.Dataset()
        user = factories.User()
        capacity1 = "editor"
        capacity2 = "member"

        helpers.call_action(
            "package_collaborator_create",
            id=dataset1["id"],
            user_id=user["id"],
            capacity=capacity1,
        )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset2["id"],
            user_id=user["id"],
            capacity=capacity2,
        )

        datasets = helpers.call_action(
            "package_collaborator_list_for_user",
            id=user["id"],
            capacity="editor",
        )

        assert len(datasets) == 1

        assert datasets[0]["package_id"] == dataset1["id"]
        assert datasets[0]["capacity"] == capacity1

    def test_list_for_user_user_not_found(self):

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action("package_collaborator_list_for_user", id="xxx")

    def test_list_for_user_wrong_capacity(self):
        user = factories.User()
        capacity = "unknown"

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "package_collaborator_list_for_user",
                id=user["id"],
                capacity=capacity,
            )


@pytest.mark.usefixtures("clean_db", "clean_index")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestCollaboratorsSearch(object):
    def test_search_results_editor(self):

        org = factories.Organization()
        dataset1 = factories.Dataset(
            name="test1", private=True, owner_org=org["id"]
        )
        dataset2 = factories.Dataset(name="test2")

        user = factories.User()
        context = {"user": user["name"], "ignore_auth": False}

        results = helpers.call_action(
            "package_search", context=context, q="*:*", include_private=True
        )

        assert results["count"] == 1
        assert results["results"][0]["id"] == dataset2["id"]

        helpers.call_action(
            "package_collaborator_create",
            id=dataset1["id"],
            user_id=user["id"],
            capacity="editor",
        )

        results = helpers.call_action(
            "package_search",
            context=context,
            q="*:*",
            include_private=True,
            sort="name asc",
        )

        assert results["count"] == 2

        assert results["results"][0]["id"] == dataset1["id"]
        assert results["results"][1]["id"] == dataset2["id"]

    def test_search_results_member(self):

        org = factories.Organization()
        dataset1 = factories.Dataset(
            name="test1", private=True, owner_org=org["id"]
        )
        dataset2 = factories.Dataset(name="test2")

        user = factories.User()
        context = {"user": user["name"], "ignore_auth": False}

        results = helpers.call_action(
            "package_search", context=context, q="*:*", include_private=True
        )

        assert results["count"] == 1
        assert results["results"][0]["id"] == dataset2["id"]

        helpers.call_action(
            "package_collaborator_create",
            id=dataset1["id"],
            user_id=user["id"],
            capacity="member",
        )

        results = helpers.call_action(
            "package_search",
            context=context,
            q="*:*",
            include_private=True,
            sort="name asc",
        )

        assert results["count"] == 2

        assert results["results"][0]["id"] == dataset1["id"]
        assert results["results"][1]["id"] == dataset2["id"]


@pytest.mark.usefixtures("clean_db")
class TestResourceSearch(object):
    def test_required_fields(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_search")
        helpers.call_action("resource_search", query="name:*")

    def test_base_search(self):
        factories.Resource(name="one")
        factories.Resource(name="two")
        result = helpers.call_action("resource_search", query="name:three")
        assert not result["count"]

        result = helpers.call_action("resource_search", query="name:one")
        assert result["count"] == 1

        result = helpers.call_action("resource_search", query="name:")
        assert result["count"] == 2

    def test_date_search(self):
        res = factories.Resource()
        result = helpers.call_action(
            "resource_search", query="created:" + res["created"]
        )
        assert result["count"] == 1

    def test_number_search(self):
        factories.Resource(size=10)
        result = helpers.call_action("resource_search", query="size:10")
        assert result["count"] == 1

    def test_resource_search_across_multiple_fields(self):
        factories.Resource(description="indexed resource", format="json")
        result = helpers.call_action(
            "resource_search", query=["description:index", "format:json"]
        )
        assert result["count"] == 1
        resource = result["results"][0]
        assert "index" in resource["description"].lower()
        assert "json" in resource["format"].lower()

    def test_resource_search_test_percentage_is_escaped(self):
        factories.Resource(description="indexed resource", format="json")
        result = helpers.call_action(
            "resource_search", query="description:index%"
        )
        assert result == {"count": 0, "results": []}


@pytest.mark.usefixtures("non_clean_db")
class TestUserPluginExtras(object):
    def test_returned_if_sysadmin_and_include_plugin_extras_only(self):

        sysadmin = factories.Sysadmin()

        user = factories.User(plugin_extras={"plugin1": {"key1": "value1"}})

        context = {"user": sysadmin["name"], "ignore_auth": False}
        user = helpers.call_action(
            "user_show",
            context=context,
            id=user["id"],
            include_plugin_extras=True,
        )

        assert user["plugin_extras"] == {"plugin1": {"key1": "value1"}}

        context = {"user": sysadmin["name"], "ignore_auth": False}
        user = helpers.call_action("user_show", context=context, id=user["id"])

        assert "plugin_extras" not in user

        context = {"user": user["name"], "ignore_auth": False}
        user = helpers.call_action(
            "user_show",
            context=context,
            id=user["id"],
            include_plugin_extras=True,
        )

        assert "plugin_extras" not in user


@pytest.mark.usefixtures("non_clean_db")
class TestGroupPackageShow:
    def test_group_package_show(self):
        group = factories.Group()
        factories.Dataset()
        pkg = factories.Dataset(groups=[{"id": group["id"]}])
        group_packages = helpers.call_action(
            "group_package_show", id=group["id"]
        )
        assert len(group_packages) == 1
        assert group_packages[0]["name"] == pkg["name"]


@pytest.mark.usefixtures("non_clean_db")
class TestGetSiteUser:
    def test_get_site_user_not_authorized(self, ckan_config):
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth("get_site_user", {"model": model, "user": ""})

        assert helpers.call_auth(
            "get_site_user", {"model": model, "user": "", "ignore_auth": True}
        )


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestPackageList:
    @pytest.mark.usefixtures("app")
    def test_package_list(self):
        pkg1 = factories.Dataset()
        pkg2 = factories.Dataset()
        packages = helpers.call_action("package_list")
        assert len(packages) == 2
        assert set(packages) == {pkg1["name"], pkg2["name"]}

    def test_package_list_private(self):
        org = factories.Organization()
        pkg1 = factories.Dataset()
        factories.Dataset(private=True, owner_org=org["id"])
        packages = helpers.call_action("package_list")
        assert packages == [pkg1["name"]]


@pytest.mark.usefixtures("clean_db")
class TestPackagePluginData(object):

    def test_returned_if_sysadmin_and_include_plugin_data_only(self):
        sysadmin = factories.Sysadmin()
        user = factories.User()

        dataset = factories.Dataset(
            plugin_data={
                "plugin1": {
                    "key1": "value1"
                }
            }
        )
        context = {
            "user": sysadmin["name"],
            "ignore_auth": False,
            "auth_user_obj": model.User.get(sysadmin["name"])
        }
        # sysadmin and include_plugin_data = True
        pkg_dict = helpers.call_action(
            "package_show",
            context=context,
            id=dataset["id"],
            include_plugin_data=True
        )
        assert pkg_dict["plugin_data"] == {
            "plugin1": {
                "key1": "value1"
            }
        }

        # sysadmin and include_plugin_data = False
        pkg_dict = helpers.call_action(
            "package_show", context=context, id=dataset["id"]
        )
        assert "plugin_data" not in pkg_dict

        # non-sysadmin and include_plugin_data = True
        context = {
            "user": user["name"],
            "ignore_auth": False,
        }
        pkg_dict = helpers.call_action(
            "package_show",
            context=context,
            id=dataset["id"],
            include_plugin_data=True
        )
        assert "plugin_data" not in pkg_dict
