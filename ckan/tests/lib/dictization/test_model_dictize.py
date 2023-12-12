# encoding: utf-8

import datetime
import operator
import copy
from pprint import pformat

import pytest

from ckan import model
from ckan.logic.schema import (
    default_create_package_schema,
    default_update_package_schema,
    default_group_schema,
    default_tags_schema,
)
from ckan.lib.navl.dictization_functions import validate
from ckan.lib.dictization import model_dictize, model_save
from ckan.lib.dictization.model_dictize import package_dictize, group_dictize
from ckan.tests import factories


@pytest.mark.usefixtures("non_clean_db")
class TestGroupListDictize:
    def test_group_list_dictize(self):
        group = factories.Group.model()
        context = {"model": model, "session": model.Session}

        group_dicts = model_dictize.group_list_dictize([group], context)

        assert len(group_dicts) == 1
        assert group_dicts[0]["name"] == group.name
        assert group_dicts[0]["package_count"] == 0
        assert "extras" not in group_dicts[0]
        assert "tags" not in group_dicts[0]
        assert "groups" not in group_dicts[0]

    def test_group_list_dictize_sorted(self):
        # we need to set the title because group_list_dictze by default sorts
        # them per display_name
        group1 = factories.Group(title="aa")
        group2 = factories.Group(title="bb")
        group_list = [model.Group.get(group2["name"]), model.Group.get(group1["name"])]
        context = {"model": model, "session": model.Session}

        group_dicts = model_dictize.group_list_dictize(group_list, context)

        # list is resorted by name
        assert group_dicts[0]["name"] == group1["name"]
        assert group_dicts[1]["name"] == group2["name"]

    def test_group_list_dictize_reverse_sorted(self):
        # we need to set the title because group_list_dictze by default sorts
        # them per display_name
        group1 = factories.Group(title="aa")
        group2 = factories.Group(title="bb")
        group_list = [model.Group.get(group1["name"]), model.Group.get(group2["name"])]
        context = {"model": model, "session": model.Session}

        group_dicts = model_dictize.group_list_dictize(
            group_list, context, reverse=True
        )

        assert group_dicts[0]["name"] == group2["name"]
        assert group_dicts[1]["name"] == group1["name"]

    def test_group_list_dictize_sort_by_package_count(self):
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Dataset(groups=[{"name": group1["name"]}, {"name": group2["name"]}])
        factories.Dataset(groups=[{"name": group2["name"]}])
        group_list = [model.Group.get(group2["name"]), model.Group.get(group1["name"])]
        context = {"model": model, "session": model.Session}

        group_dicts = model_dictize.group_list_dictize(
            group_list,
            context,
            sort_key=lambda x: x["package_count"],
            with_package_counts=True,
        )

        # list is resorted by package counts
        assert group_dicts[0]["name"] == group1["name"]
        assert group_dicts[1]["name"] == group2["name"]

    def test_group_list_dictize_without_package_count(self):
        group_ = factories.Group()
        factories.Dataset(groups=[{"name": group_["name"]}])
        group_list = [model.Group.get(group_["name"])]
        context = {"model": model, "session": model.Session}

        group_dicts = model_dictize.group_list_dictize(
            group_list, context, with_package_counts=False
        )

        assert "packages" not in group_dicts[0]

    def test_group_list_dictize_including_extras(self):
        group = factories.Group.model(extras=[{"key": "k1", "value": "v1"}])
        context = {"model": model, "session": model.Session}

        group_dicts = model_dictize.group_list_dictize(
            [group], context, include_extras=True
        )

        assert group_dicts[0]["extras"][0]["key"] == "k1"

    def test_group_list_dictize_including_tags(self):
        group = factories.Group.model()
        tag = factories.Tag.model()
        member = model.Member(
            group=group, table_id=tag.id, table_name="tag"
        )
        model.Session.add(member)
        model.Session.commit()
        context = {"model": model, "session": model.Session}

        group_dicts = model_dictize.group_list_dictize(
            [group], context, include_tags=True
        )

        assert group_dicts[0]["tags"][0]["name"] == tag.name

    @pytest.mark.usefixtures("clean_db")
    def test_group_list_dictize_including_groups(self):
        parent = factories.Group(title="Parent")
        child = factories.Group(title="Child", groups=[{"name": parent["name"]}])
        group_list = [model.Group.get(parent["name"]), model.Group.get(child["name"])]
        context = {"model": model, "session": model.Session}

        child_dict, parent_dict = model_dictize.group_list_dictize(
            group_list, context, sort_key=operator.itemgetter("title"),
            include_groups=True
        )

        assert parent_dict["name"] == parent["name"]
        assert child_dict["name"] == child["name"]
        assert parent_dict["groups"] == []
        assert child_dict["groups"][0]["name"] == parent["name"]


@pytest.mark.usefixtures("non_clean_db")
class TestGroupDictize:
    def test_group_dictize(self):
        group_obj = factories.Group.model()
        context = {"model": model, "session": model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert group["name"] == group_obj.name
        assert group["packages"] == []
        assert group["extras"] == []
        assert group["tags"] == []
        assert group["groups"] == []

    def test_group_dictize_group_with_dataset(self):
        group_obj = factories.Group.model()
        package = factories.Dataset(groups=[{"name": group_obj.name}])
        context = {"model": model, "session": model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert group["packages"][0]["name"] == package["name"]
        assert group["packages"][0]["groups"][0]["name"] == group_obj.name

    def test_group_dictize_group_with_extra(self):
        group_obj = factories.Group.model(extras=[{"key": "k1", "value": "v1"}])
        context = {"model": model, "session": model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert group["extras"][0]["key"] == "k1"

    def test_group_dictize_group_with_parent_group(self):
        parent = factories.Group(title="Parent")
        group_obj = factories.Group.model(title="Child", groups=[{"name": parent["name"]}])
        context = {"model": model, "session": model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert len(group["groups"]) == 1
        assert group["groups"][0]["name"] == parent["name"]
        assert group["groups"][0]["package_count"] == 0

    def test_group_dictize_without_packages(self):
        # group_list_dictize might not be interested in packages at all
        # so sets these options. e.g. it is not all_fields nor are the results
        # sorted by the number of packages.
        group_obj = factories.Group.model()
        context = {"model": model, "session": model.Session}

        group = model_dictize.group_dictize(
            group_obj, context, packages_field=None
        )

        assert "packages" not in group

    def test_group_dictize_with_package_list(self):
        group_obj = factories.Group.model()
        package = factories.Dataset(groups=[{"name": group_obj.name}])
        context = {"model": model, "session": model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert isinstance(group["packages"], list)
        assert len(group["packages"]) == 1
        assert group["packages"][0]["name"] == package["name"]

    def test_group_dictize_with_package_list_limited(self):
        """
        Packages returned in group are limited by context var.
        """
        group_obj = factories.Group.model()
        for _ in range(5):
            factories.Dataset(groups=[{"name": group_obj.name}])
        # limit packages to 4
        context = {
            "model": model,
            "session": model.Session,
            "limits": {"packages": 4},
        }

        group = model_dictize.group_dictize(group_obj, context)

        assert len(group["packages"]) == 4

    def test_group_dictize_with_package_list_limited_over(self):
        """
        Packages limit is set higher than number of packages in group.
        """
        group_obj = factories.Group.model()
        for _ in range(3):
            factories.Dataset(groups=[{"name": group_obj.name}])
        # limit packages to 4
        context = {
            "model": model,
            "session": model.Session,
            "limits": {"packages": 4},
        }

        group = model_dictize.group_dictize(group_obj, context)

        assert len(group["packages"]) == 3

    @pytest.mark.ckan_config("ckan.search.rows_max", "4")
    def test_group_dictize_with_package_list_limited_by_config(self):
        group_obj = factories.Group.model()
        for _ in range(5):
            factories.Dataset(groups=[{"name": group_obj.name}])

        context = {"model": model, "session": model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert len(group["packages"]) == 4
        # limited by ckan.search.rows_max

    def test_group_dictize_with_package_count(self):
        # group_list_dictize calls it like this by default
        group_obj = factories.Group.model()
        other_group_obj = factories.Group.model()
        factories.Dataset(groups=[{"name": group_obj.name}])
        factories.Dataset(groups=[{"name": other_group_obj.name}])
        context = {
            "model": model,
            "session": model.Session,
            "dataset_counts": model_dictize.get_group_dataset_counts(),
        }

        group = model_dictize.group_dictize(
            group_obj, context, packages_field="dataset_count"
        )
        assert group["package_count"] == 1

    def test_group_dictize_with_no_packages_field_but_still_package_count(
        self,
    ):
        # logic.get.group_show calls it like this when not include_datasets
        group_obj = factories.Group.model()
        factories.Dataset(groups=[{"name": group_obj.name}])
        context = {"model": model, "session": model.Session}
        # not supplying dataset_counts in this case either

        group = model_dictize.group_dictize(
            group_obj, context, packages_field="dataset_count"
        )

        assert "packages" not in group
        assert group["package_count"] == 1

    def test_group_dictize_for_org_with_package_list(self):
        group_obj = factories.Organization.model()
        package = factories.Dataset(owner_org=group_obj.id)
        context = {"model": model, "session": model.Session}

        org = model_dictize.group_dictize(group_obj, context)

        assert isinstance(org["packages"], list)
        assert len(org["packages"]) == 1
        assert org["packages"][0]["name"] == package["name"]

    def test_group_dictize_for_org_with_package_count(self):
        # group_list_dictize calls it like this by default
        org_obj = factories.Organization.model()
        other_org_ = factories.Organization()
        factories.Dataset(owner_org=org_obj.id)
        factories.Dataset(owner_org=other_org_["id"])
        context = {
            "model": model,
            "session": model.Session,
            "dataset_counts": model_dictize.get_group_dataset_counts(),
        }

        org = model_dictize.group_dictize(
            org_obj, context, packages_field="dataset_count"
        )

        assert org["package_count"] == 1

    @pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
    def test_group_dictize_for_org_with_private_package_count_collaborator(
        self,
    ):
        import ckan.tests.helpers as helpers

        org_obj = factories.Organization.model()
        user_obj = factories.User.model()
        private_dataset = factories.Dataset(owner_org=org_obj.id, private=True)
        factories.Dataset(owner_org=org_obj.id)
        context = {
            "model": model,
            "session": model.Session,
            "auth_user_obj": user_obj,
        }
        org = model_dictize.group_dictize(org_obj, context)
        assert org["package_count"] == 1

        helpers.call_action(
            "package_collaborator_create",
            id=private_dataset["id"],
            user_id=user_obj.id,
            capacity="member",
        )
        org = model_dictize.group_dictize(org_obj, context)
        assert org["package_count"] == 2


@pytest.mark.usefixtures("non_clean_db")
class TestPackageDictize:
    def remove_changable_values(self, dict_):
        dict_ = copy.deepcopy(dict_)
        for key, value in list(dict_.items()):
            if key.endswith("id") and key != "license_id":
                dict_.pop(key)
            if key == "created":
                dict_.pop(key)
            if "timestamp" in key:
                dict_.pop(key)
            if key in ["metadata_created", "metadata_modified"]:
                dict_.pop(key)
            if isinstance(value, list):
                for i, sub_dict in enumerate(value):
                    value[i] = self.remove_changable_values(sub_dict)
        return dict_

    def assert_equals_expected(self, expected_dict, result_dict):
        result_dict = self.remove_changable_values(result_dict)
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

    def test_package_dictize_basic(self):
        dataset = factories.Dataset(
            notes="Some *description*",
            url="http://example.com",
        )
        dataset_obj = model.Package.get(dataset["id"])
        context = {"model": model, "session": model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert result["name"] == dataset["name"]
        assert not (result["isopen"])
        assert result["type"] == dataset["type"]
        today = datetime.date.today().strftime("%Y-%m-%d")
        assert result["metadata_modified"].startswith(today)
        assert result["metadata_created"].startswith(today)
        assert result["creator_user_id"] == dataset_obj.creator_user_id
        expected_dict = {
            "author": dataset["author"],
            "author_email": dataset["author_email"],
            "extras": dataset["extras"],
            "groups": dataset["groups"],
            "isopen": dataset["isopen"],
            "license_id": dataset["license_id"],
            "license_title": dataset["license_title"],
            "maintainer": dataset["maintainer"],
            "maintainer_email": dataset["maintainer_email"],
            "name": dataset["name"],
            "notes": dataset["notes"],
            "num_resources": dataset["num_resources"],
            "num_tags": dataset["num_tags"],
            "organization": dataset["organization"],
            "owner_org": dataset["owner_org"],
            "private": dataset["private"],
            "relationships_as_object": dataset["relationships_as_object"],
            "relationships_as_subject": dataset["relationships_as_subject"],
            "resources": dataset["resources"],
            "state": dataset["state"],
            "tags": dataset["tags"],
            "title": dataset["title"],
            "type": dataset["type"],
            "url": dataset["url"],
            "version": dataset["version"],
        }
        self.assert_equals_expected(expected_dict, result)

    def test_package_dictize_license(self):
        dataset = factories.Dataset(license_id="cc-by")
        dataset_obj = model.Package.get(dataset["id"])
        context = {"model": model, "session": model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert result["isopen"]
        assert result["license_id"] == "cc-by"
        assert (
            result["license_url"]
            == "http://www.opendefinition.org/licenses/cc-by"
        )
        assert result["license_title"] == "Creative Commons Attribution"

    def test_package_dictize_title_stripped_of_whitespace(self):
        dataset = factories.Dataset(title=" has whitespace \t")
        dataset_obj = model.Package.get(dataset["id"])
        context = {"model": model, "session": model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert result["title"] == "has whitespace"
        assert dataset_obj.title == " has whitespace \t"

    def test_package_dictize_resource(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package_id=dataset["id"], name="test_pkg_dictize"
        )
        dataset_obj = model.Package.get(dataset["id"])
        context = {"model": model, "session": model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal_for_keys(result["resources"][0], resource, "name", "url")
        expected_dict = {
            u"cache_last_updated": resource["cache_last_updated"],
            u"cache_url": resource["cache_url"],
            u"description": resource["description"],
            u"format": resource["format"],
            u"hash": resource["hash"],
            u"last_modified": resource["last_modified"],
            u"mimetype": resource["mimetype"],
            u"mimetype_inner": resource["mimetype_inner"],
            u"name": resource["name"],
            u"position": resource["position"],
            u"resource_type": resource["resource_type"],
            u"size": resource["size"],
            u"state": resource["state"],
            u"url": resource["url"],
            u"url_type": resource["url_type"],
        }
        self.assert_equals_expected(expected_dict, result["resources"][0])

    def test_package_dictize_resource_upload_and_striped(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset["id"],
            name="test_pkg_dictize",
            url_type="upload",
            url="some_filename.csv",
        )

        context = {"model": model, "session": model.Session}

        result = model_save.resource_dict_save(resource, context)

        expected_dict = {u"url": u"some_filename.csv", u"url_type": u"upload"}
        assert expected_dict["url"] == result.url

    def test_package_dictize_resource_upload_with_url_and_striped(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset["id"],
            name="test_pkg_dictize",
            url_type="upload",
            url="http://some_filename.csv",
        )

        context = {"model": model, "session": model.Session}

        result = model_save.resource_dict_save(resource, context)

        expected_dict = {u"url": u"some_filename.csv", u"url_type": u"upload"}
        assert expected_dict["url"] == result.url

    def test_package_dictize_tags(self):
        tag = factories.Tag.stub().name
        dataset = factories.Dataset(tags=[{"name": tag}])
        dataset_obj = model.Package.get(dataset["id"])
        context = {"model": model, "session": model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert result["tags"][0]["name"] == tag
        expected_dict = {
            "display_name": tag,
            u"name": tag,
            u"state": u"active",
        }
        self.assert_equals_expected(expected_dict, result["tags"][0])

    def test_package_dictize_extras(self):
        extras_dict = {"key": "latitude", "value": "54.6"}
        dataset = factories.Dataset(extras=[extras_dict])
        dataset_obj = model.Package.get(dataset["id"])
        context = {"model": model, "session": model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal_for_keys(result["extras"][0], extras_dict, "key", "value")
        expected_dict = {
            u"key": u"latitude",
            u"state": u"active",
            u"value": u"54.6",
        }
        self.assert_equals_expected(expected_dict, result["extras"][0])

    def test_package_dictize_group(self):
        group = factories.Group(
            title="Test Group Dictize"
        )
        dataset = factories.Dataset(groups=[{"name": group["name"]}])
        dataset_obj = model.Package.get(dataset["id"])
        context = {"model": model, "session": model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal_for_keys(result["groups"][0], group, "name")
        expected_dict = {
            u"approval_status": group["approval_status"],
            u"capacity": "public",
            u"description": group["description"],
            "display_name": group["display_name"],
            "image_display_url": group["image_display_url"],
            u"image_url": group["image_url"],
            u"is_organization": group["is_organization"],
            u"name": group["name"],
            u"state": group["state"],
            u"title": group["title"],
            u"type": group["type"],
        }
        self.assert_equals_expected(expected_dict, result["groups"][0])

    def test_package_dictize_owner_org(self):
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        dataset_obj = model.Package.get(dataset["id"])
        context = {"model": model, "session": model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert result["owner_org"] == org["id"]
        assert_equal_for_keys(result["organization"], org, "name")
        expected_dict = {
            u"approval_status": org["approval_status"],
            u"description": org["description"],
            u"image_url": org["image_url"],
            u"is_organization": org["is_organization"],
            u"name": org["name"],
            u"state": org["state"],
            u"title": org["title"],
            u"type": org["type"],
        }
        self.assert_equals_expected(expected_dict, result["organization"])


def assert_equal_for_keys(dict1, dict2, *keys):
    for key in keys:
        assert key in dict1, 'Dict 1 misses key "%s"' % key
        assert key in dict2, 'Dict 2 misses key "%s"' % key
        assert dict1[key] == dict2[key], "%s != %s (key=%s)" % (
            dict1[key],
            dict2[key],
            key,
        )


@pytest.mark.usefixtures("non_clean_db")
class TestTagDictize(object):
    """Unit tests for the tag_dictize() function."""

    def test_tag_dictize_including_datasets(self):
        """By default a dictized tag should include the tag's datasets."""
        tag_name = factories.Tag.stub().name
        # Make a dataset in order to have a tag created.
        factories.Dataset(tags=[dict(name=tag_name)])
        tag = model.Tag.get(tag_name)

        tag_dict = model_dictize.tag_dictize(tag, context={"model": model})

        assert len(tag_dict["packages"]) == 1

    def test_tag_dictize_not_including_datasets(self):
        """include_datasets=False should exclude datasets from tag dicts."""
        tag_name = factories.Tag.stub().name
        # Make a dataset in order to have a tag created.
        factories.Dataset(tags=[dict(name=tag_name)])
        tag = model.Tag.get(tag_name)

        tag_dict = model_dictize.tag_dictize(
            tag, context={"model": model}, include_datasets=False
        )

        assert not tag_dict.get("packages")


class TestVocabularyDictize(object):
    """Unit tests for the vocabulary_dictize() function."""

    def test_vocabulary_dictize_including_datasets(self):
        """include_datasets=True should include datasets in vocab dicts."""
        tag1 = factories.Tag.stub().name
        tag2 = factories.Tag.stub().name
        vocab_dict = factories.Vocabulary(
            tags=[dict(name=tag1), dict(name=tag2)]
        )
        factories.Dataset(tags=vocab_dict["tags"])
        vocab_obj = model.Vocabulary.get(vocab_dict["name"])

        vocab_dict = model_dictize.vocabulary_dictize(
            vocab_obj, context={"model": model}, include_datasets=True
        )

        assert len(vocab_dict["tags"]) == 2
        for tag in vocab_dict["tags"]:
            assert len(tag["packages"]) == 1

    def test_vocabulary_dictize_not_including_datasets(self):
        """By default datasets should not be included in vocab dicts."""
        tag1 = factories.Tag.stub().name
        tag2 = factories.Tag.stub().name

        vocab_dict = factories.Vocabulary(
            tags=[dict(name=tag1), dict(name=tag2)]
        )
        factories.Dataset(tags=vocab_dict["tags"])
        vocab_obj = model.Vocabulary.get(vocab_dict["name"])

        vocab_dict = model_dictize.vocabulary_dictize(
            vocab_obj, context={"model": model}
        )

        assert len(vocab_dict["tags"]) == 2
        for tag in vocab_dict["tags"]:
            assert len(tag.get("packages", [])) == 0


@pytest.mark.usefixtures("non_clean_db")
class TestPackageSchema(object):
    def remove_changable_columns(self, dict):
        for key, value in list(dict.items()):
            if key.endswith("id") and key != "license_id":
                dict.pop(key)
            if key in ("created", "metadata_modified"):
                dict.pop(key)

            if isinstance(value, list):
                for new_dict in value:
                    self.remove_changable_columns(new_dict)
        return dict

    def test_package_schema(self):
        group1 = factories.Group(title="Dave's books")
        group2 = factories.Group(title="Roger's books")
        first_name = factories.Dataset.stub().name
        second_name = factories.Dataset.stub().name
        expected_data = {
            "extras": [
                {"key": u"genre", "value": u"romantic novel"},
                {"key": u"original media", "value": u"book"},
            ],
            "groups": [
                {u"name": group1["name"], u"title": group1["title"]},
                {u"name": group2["name"], u"title": group2["title"]},
            ],
            "license_id": u"other-open",
            "name": first_name,
            "type": u"dataset",
            "notes": u"Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n\nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n",
            "private": False,
            "resources": [
                {
                    "alt_url": u"alt123",
                    "description": u'Full text. Needs escaping: " Umlaut: \xfc',
                    "format": u"plain text",
                    "hash": u"abc123",
                    "size_extra": u"123",
                    "url": u"http://datahub.io/download/x=1&y=2",
                },
                {
                    "alt_url": u"alt345",
                    "description": u"Index of the novel",
                    "format": u"JSON",
                    "hash": u"def456",
                    "size_extra": u"345",
                    "url": u"http://datahub.io/index.json",
                },
            ],
            "tags": sorted([
                {"name": factories.Tag.stub().name},
                {"name": factories.Tag.stub().name},
                {"name": factories.Tag.stub().name},
            ], key=operator.itemgetter("name")),
            "title": u"A Novel By Tolstoy",
            "url": u"http://datahub.io",
            "version": u"0.7a",
            "relationships_as_subject": [],
            "relationships_as_object": [],
        }

        context = {"model": model, "session": model.Session}
        pkg = factories.Dataset.model(**expected_data)

        package_id = pkg.id
        result = package_dictize(pkg, context)
        self.remove_changable_columns(result)

        result["name"] = second_name
        expected_data["name"] = second_name
        converted_data, errors = validate(
            result, default_create_package_schema(), context
        )

        assert converted_data == expected_data, pformat(converted_data)
        assert not errors, errors

        data = converted_data
        data["name"] = first_name
        data.pop("title")
        data["resources"][0]["url"] = "fsdfafasfsaf"
        data["resources"][1].pop("url")

        converted_data, errors = validate(
            data, default_create_package_schema(), context
        )

        assert errors == {"name": [u"That URL is already in use."]}, pformat(
            errors
        )

        data["id"] = package_id
        data["name"] = "????jfaiofjioafjij"

        converted_data, errors = validate(
            data, default_update_package_schema(), context
        )
        assert errors == {
            "name": [
                u"Must be purely lowercase alphanumeric (ascii) "
                "characters and these symbols: -_"
            ]
        }, pformat(errors)

    @pytest.mark.usefixtures("clean_index")
    def test_group_schema(self):
        group = factories.Group.model()
        context = {"model": model, "session": model.Session}
        factories.Dataset.create_batch(2, groups=[{"name": group.name}])

        data = group_dictize(group, context)

        # we don't want these here
        del data["groups"]
        del data["users"]
        del data["tags"]
        del data["extras"]

        converted_data, errors = validate(
            data, default_group_schema(), context
        )
        assert not errors
        group_pack = sorted(group.packages(), key=operator.attrgetter("id"))

        converted_data["packages"] = sorted(
            converted_data["packages"], key=operator.itemgetter("id")
        )

        expected = {
            "description": group.description,
            "id": group.id,
            "name": group.name,
            "is_organization": False,
            "type": u"group",
            "image_url": group.image_url,
            "image_display_url": group.image_url,
            "packages": sorted(
                [
                    {
                        "id": group_pack[0].id,
                        "name": group_pack[0].name,
                        "title": group_pack[0].title,
                    },
                    {
                        "id": group_pack[1].id,
                        "name": group_pack[1].name,
                        "title": group_pack[1].title,
                    },
                ],
                key=operator.itemgetter("id"),
            ),
            "title": group.title,
            "approval_status": u"approved",
        }

        assert converted_data == expected, pformat(converted_data)

        data["packages"].sort(key=lambda x: x["id"])
        data["packages"][0]["id"] = factories.Dataset.stub().name
        data["packages"][1].pop("id")
        data["packages"][1].pop("name")

        converted_data, errors = validate(
            data, default_group_schema(), context
        )
        assert errors == {
            "packages": [
                {"id": [u"Not found: Dataset"]},
                {"id": [u"Missing value"]},
            ]
        }, pformat(errors)


class TestTagSchema:
    def test_tag_schema_allows_spaces(self):
        """Asserts that a tag name with space is valid"""
        ignored = ""
        context = {"model": model, "session": model.Session}
        data = {
            "name": u"with space",
            "revision_timestamp": ignored,
            "state": ignored,
        }
        _, errors = validate(data, default_tags_schema(), context)
        assert not errors, str(errors)

    def test_tag_schema_allows_limited_punctuation(self):
        """Asserts that a tag name with limited punctuation is valid"""
        ignored = ""
        context = {"model": model, "session": model.Session}
        data = {
            "name": u".-_",
            "revision_timestamp": ignored,
            "state": ignored,
        }
        _, errors = validate(data, default_tags_schema(), context)
        assert not errors, str(errors)

    def test_tag_schema_allows_capital_letters(self):
        """Asserts that tag names can have capital letters"""
        ignored = ""
        context = {"model": model, "session": model.Session}
        data = {
            "name": u"CAPITALS",
            "revision_timestamp": ignored,
            "state": ignored,
        }
        _, errors = validate(data, default_tags_schema(), context)
        assert not errors, str(errors)

    def test_tag_schema_disallows_most_punctuation(self):
        """Asserts most punctuation is disallowed"""
        not_allowed = r'!?"\'+=:;@#~[]{}()*&^%$,'
        context = {"model": model, "session": model.Session}
        ignored = ""
        data = {"revision_timestamp": ignored, "state": ignored}
        for ch in not_allowed:
            data["name"] = "Character " + ch
            _, errors = validate(data, default_tags_schema(), context)
            assert errors
            assert "name" in errors
            error_message = errors["name"][0]
            assert data["name"] in error_message, error_message
            assert "can only contain alphanumeric characters" in error_message

    def test_tag_schema_disallows_whitespace_other_than_spaces(self):
        """Asserts whitespace characters, such as tabs, are not allowed."""
        not_allowed = "\t\n\r\f\v"
        context = {"model": model, "session": model.Session}
        ignored = ""
        data = {"revision_timestamp": ignored, "state": ignored}
        for ch in not_allowed:
            data["name"] = "Bad " + ch + " character"
            _, errors = validate(data, default_tags_schema(), context)
            assert errors, repr(ch)
            assert "name" in errors
            error_message = errors["name"][0]
            assert data["name"] in error_message, error_message
            assert "can only contain alphanumeric characters" in error_message
