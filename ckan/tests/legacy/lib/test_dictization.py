# encoding: utf-8


import pytest

from pprint import pformat
from difflib import unified_diff

import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
from ckan import model
from ckan.lib.dictization import table_dictize, table_dict_save

from ckan.lib.dictization.model_dictize import (
    package_dictize,
    resource_dictize,
    package_to_api1,
    package_to_api2,
    user_dictize,
)
from ckan.lib.dictization.model_save import (
    package_dict_save,
    resource_dict_save,
    activity_dict_save,
    package_api_to_dict,
    group_api_to_dict,
    package_tag_list_save,
)
import ckan.logic.action.get


class TestBasicDictize:
    @pytest.fixture(autouse=True)
    def initial_data(self):
        # clean the db so we can run these tests on their own
        model.repo.rebuild_db()
        search.clear_all()
        CreateTestData.create()
        yield
        model.repo.rebuild_db()
        model.Session.remove()

    def remove_changable_columns(self, dict, remove_package_id=False):
        ids_to_keep = ["license_id", "creator_user_id"]
        if not remove_package_id:
            ids_to_keep.append("package_id")

        for key, value in list(dict.items()):
            if key.endswith("id") and key not in ids_to_keep:
                dict.pop(key)
            if key == "created":
                dict.pop(key)
            if "timestamp" in key:
                dict.pop(key)
            if key in ["metadata_created", "metadata_modified"]:
                dict.pop(key)
            if isinstance(value, list):
                for new_dict in value:
                    self.remove_changable_columns(
                        new_dict,
                        key in ["resources", "extras"] or remove_package_id,
                    )
        return dict

    def test_03_package_to_api1(self):

        context = {"model": model, "session": model.Session}

        pkg = (
            model.Session.query(model.Package)
            .filter_by(name="annakarenina")
            .first()
        )

        asdict = pkg.as_dict()
        asdict["download_url"] = asdict["resources"][0]["url"]
        asdict["license_title"] = u"Other (Open)"
        asdict["num_tags"] = 3
        asdict["num_resources"] = 2

        dictize = package_to_api1(pkg, context)
        # the is_dict method doesn't care about organizations
        del dictize["organization"]
        assert dictize == asdict

    def test_04_package_to_api1_with_relationship(self):

        context = {"model": model, "session": model.Session}

        create = CreateTestData

        create.create_family_test_data()
        pkg = model.Session.query(model.Package).filter_by(name="homer").one()

        as_dict = dict(pkg.as_dict())
        as_dict["license_title"] = None
        as_dict["num_tags"] = 0
        as_dict["num_resources"] = 0
        dictize = package_to_api1(pkg, context)

        as_dict["relationships"].sort(key=lambda x: list(x.items()))
        dictize["relationships"].sort(key=lambda x: list(x.items()))
        # the is_dict method doesn't care about organizations
        del dictize["organization"]
        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)

        assert as_dict == dictize, "\n".join(
            unified_diff(
                as_dict_string.split("\n"), dictize_string.split("\n")
            )
        )

    def test_05_package_to_api2(self):

        context = {"model": model, "session": model.Session}

        pkg = (
            model.Session.query(model.Package)
            .filter_by(name="annakarenina")
            .first()
        )

        as_dict = pkg.as_dict(ref_package_by="id", ref_group_by="id")
        dictize = package_to_api2(pkg, context)

        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)

        assert package_to_api2(pkg, context) == dictize, "\n".join(
            unified_diff(
                as_dict_string.split("\n"), dictize_string.split("\n")
            )
        )

    def test_06_package_to_api2_with_relationship(self):

        context = {"model": model, "session": model.Session}

        create = CreateTestData
        create.create_family_test_data()

        pkg = model.Session.query(model.Package).filter_by(name="homer").one()

        as_dict = pkg.as_dict(ref_package_by="id", ref_group_by="id")
        as_dict["license_title"] = None
        as_dict["num_tags"] = 0
        as_dict["num_resources"] = 0
        dictize = package_to_api2(pkg, context)

        as_dict["relationships"].sort(key=lambda x: list(x.items()))
        dictize["relationships"].sort(key=lambda x: list(x.items()))

        # the is_dict method doesn't care about organizations
        del dictize["organization"]
        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)

        assert as_dict == dictize, "\n".join(
            unified_diff(
                as_dict_string.split("\n"), dictize_string.split("\n")
            )
        )

    def test_07_table_simple_save(self):

        context = {"model": model, "session": model.Session}

        anna1 = (
            model.Session.query(model.Package)
            .filter_by(name="annakarenina")
            .one()
        )

        anna_dictized = self.remove_changable_columns(
            table_dictize(anna1, context)
        )

        anna_dictized["name"] = "annakarenina2"

        table_dict_save(anna_dictized, model.Package, context)
        model.Session.commit()

        pkg = (
            model.Session.query(model.Package)
            .filter_by(name="annakarenina2")
            .one()
        )

        assert (
            self.remove_changable_columns(table_dictize(pkg, context))
            == anna_dictized
        ), self.remove_changable_columns(table_dictize(pkg, context))

    @pytest.mark.usefixtures("with_request_context")
    def test_08_package_save(self):

        context = {
            "model": model,
            "user": "testsysadmin",
            "session": model.Session,
        }

        anna1 = (
            model.Session.query(model.Package)
            .filter_by(name="annakarenina")
            .one()
        )

        anna_dictized = self.remove_changable_columns(
            package_dictize(anna1, context)
        )

        anna_dictized["name"] = u"annakarenina3"

        package_dict_save(anna_dictized, context)
        model.Session.commit()

        # Re-clean anna_dictized
        anna_dictized = self.remove_changable_columns(anna_dictized)

        pkg = (
            model.Session.query(model.Package)
            .filter_by(name="annakarenina3")
            .one()
        )

        package_dictized = self.remove_changable_columns(
            package_dictize(pkg, context)
        )

        anna_original = pformat(anna_dictized)
        anna_after_save = pformat(package_dictized)

        assert package_dictized == anna_dictized, "\n".join(
            unified_diff(
                anna_original.split("\n"), anna_after_save.split("\n")
            )
        )

    def test_14_resource_no_id(self):

        context = {"model": model, "session": model.Session}

        model.Session.commit()

        new_resource = {
            "mimetype": None,
            u"alt_url": u"empty resource group id",
            "hash": u"abc123",
            "description": u'Full text. Needs escaping: " Umlaut: \xfc',
            "format": u"plain text",
            "url": u"http://test_new",
            "cache_url": None,
            "cache_last_updated": None,
            "state": u"active",
            "mimetype_inner": None,
            "url_type": None,
            "last_modified": None,
            "position": 0,
            "size": None,
            "size_extra": u"123",
            "resource_type": None,
            "name": None,
            "package_id": "",  # Just so we can save
        }

        resource_dict_save(new_resource, context)
        model.Session.commit()
        model.Session.remove()

        # Remove the package id
        del new_resource["package_id"]

        res = (
            model.Session.query(model.Resource)
            .filter_by(url=u"http://test_new")
            .one()
        )

        res_dictized = self.remove_changable_columns(
            resource_dictize(res, context), True
        )

        assert res_dictized == new_resource, res_dictized

    def test_15_api_to_dictize(self):

        context = {"model": model, "api_version": 1, "session": model.Session}

        api_data = {
            "name": u"testpkg",
            "title": u"Some Title",
            "url": u"http://blahblahblah.mydomain",
            "resources": [
                {
                    u"url": u"http://blah.com/file2.xml",
                    u"format": u"xml",
                    u"description": u"Second file",
                    u"hash": u"def123",
                    u"alt_url": u"alt_url",
                    u"size": u"200",
                },
                {
                    u"url": u"http://blah.com/file.xml",
                    u"format": u"xml",
                    u"description": u"Main file",
                    u"hash": u"abc123",
                    u"alt_url": u"alt_url",
                    u"size": u"200",
                },
            ],
            "tags": u"russion novel",
            "license_id": u"gpl-3.0",
            "extras": {"genre": u"horror", "media": u"dvd"},
        }

        dictized = package_api_to_dict(api_data, context)

        assert dictized == {
            "extras": [
                {"key": "genre", "value": u"horror"},
                {"key": "media", "value": u"dvd"},
            ],
            "license_id": u"gpl-3.0",
            "name": u"testpkg",
            "resources": [
                {
                    u"alt_url": u"alt_url",
                    u"description": u"Second file",
                    u"size": u"200",
                    u"format": u"xml",
                    u"hash": u"def123",
                    u"url": u"http://blah.com/file2.xml",
                },
                {
                    u"alt_url": u"alt_url",
                    u"description": u"Main file",
                    u"size": u"200",
                    u"format": u"xml",
                    u"hash": u"abc123",
                    u"url": u"http://blah.com/file.xml",
                },
            ],
            "tags": [{"name": u"russion"}, {"name": u"novel"}],
            "title": u"Some Title",
            "url": u"http://blahblahblah.mydomain",
        }

        package_dict_save(dictized, context)
        model.Session.commit()
        model.Session.remove()

        pkg = (
            model.Session.query(model.Package).filter_by(name=u"testpkg").one()
        )

        package_dictized = self.remove_changable_columns(
            package_dictize(pkg, context)
        )

    def test_17_group_apis_to_dict(self):

        context = {"model": model, "session": model.Session}

        api_group = {
            "name": u"testgroup",
            "title": u"Some Group Title",
            "description": u"Great group!",
            "packages": [u"annakarenina", u"warandpeace"],
        }

        assert group_api_to_dict(api_group, context) == {
            "description": u"Great group!",
            "name": u"testgroup",
            "packages": [{"id": u"annakarenina"}, {"id": u"warandpeace"}],
            "title": u"Some Group Title",
        }, pformat(group_api_to_dict(api_group, context))

    def test_18_package_tag_list_save(self):
        name = u"testpkg18"
        context = {"model": model, "session": model.Session}
        pkg_dict = {"name": name}

        package = table_dict_save(pkg_dict, model.Package, context)

        tag_dicts = [{"name": "tag1"}, {"name": "tag2"}]
        package_tag_list_save(tag_dicts, package, context)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(name)
        assert set([tag.name for tag in pkg.get_tags()]) == set(
            ("tag1", "tag2")
        )

    def test_19_package_tag_list_save_duplicates(self):
        name = u"testpkg19"
        context = {"model": model, "session": model.Session}
        pkg_dict = {"name": name}

        package = table_dict_save(pkg_dict, model.Package, context)

        tag_dicts = [{"name": "tag1"}, {"name": "tag1"}]  # duplicate
        package_tag_list_save(tag_dicts, package, context)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(name)
        assert set([tag.name for tag in pkg.get_tags()]) == set(("tag1",))

    def test_20_activity_save(self):

        # Add a new Activity object to the database by passing a dict to
        # activity_dict_save()
        context = {"model": model, "session": model.Session}
        user = model.User.by_name(u"tester")
        sent = {
            "user_id": user.id,
            "object_id": user.id,
            "activity_type": "changed user",
        }
        activity_dict_save(sent, context)
        model.Session.commit()

        # Retrieve the newest Activity object from the database, check that its
        # attributes match those of the dict we saved.
        got = ckan.logic.action.get.user_activity_list(
            context, {"id": user.id}
        )[0]
        assert got["user_id"] == sent["user_id"]
        assert got["object_id"] == sent["object_id"]
        assert got["activity_type"] == sent["activity_type"]

        # The activity object should also have an ID and timestamp.
        assert got["id"]
        assert got["timestamp"]

    def test_21_package_dictization_with_deleted_group(self):
        """
        Ensure that the dictization does not return groups that the dataset has
        been removed from.
        """
        # Create a new dataset and 2 new groups
        pkg = model.Package(name="testing-deleted-groups")
        group_1 = model.Group(name="test-group-1")
        group_2 = model.Group(name="test-group-2")
        model.Session.add(pkg)
        model.Session.add(group_1)
        model.Session.add(group_2)
        model.Session.flush()

        # Add the dataset to group_1, and signal that the dataset used
        # to be a member of group_2 by setting its membership state to 'deleted'
        membership_1 = model.Member(
            table_id=pkg.id,
            table_name="package",
            group=group_1,
            group_id=group_1.id,
            state="active",
        )

        membership_2 = model.Member(
            table_id=pkg.id,
            table_name="package",
            group=group_2,
            group_id=group_2.id,
            state="deleted",
        )

        model.Session.add(membership_1)
        model.Session.add(membership_2)
        model.repo.commit()

        # Dictize the dataset
        context = {"model": model, "session": model.Session}

        result = package_dictize(pkg, context)
        self.remove_changable_columns(result)
        assert "test-group-2" not in [g["name"] for g in result["groups"]]
        assert "test-group-1" in [g["name"] for g in result["groups"]]

    @pytest.mark.usefixtures("with_request_context")
    def test_22_user_dictize_as_sysadmin(self):
        """Sysadmins should be allowed to see certain sensitive data."""
        context = {
            "model": model,
            "session": model.Session,
            "user": "testsysadmin",
        }

        user = model.User.by_name("tester")

        user_dict = user_dictize(user, context)

        # Check some of the non-sensitive data
        assert "name" in user_dict
        assert "about" in user_dict

        # Check sensitive data is available
        assert "apikey" in user_dict
        assert "email" in user_dict

        # Passwords and reset keys should never be available
        assert "password" not in user_dict
        assert "reset_key" not in user_dict

    @pytest.mark.usefixtures("with_request_context")
    def test_23_user_dictize_as_same_user(self):
        """User should be able to see their own sensitive data."""
        context = {"model": model, "session": model.Session, "user": "tester"}

        user = model.User.by_name("tester")

        user_dict = user_dictize(user, context)

        # Check some of the non-sensitive data
        assert "name" in user_dict
        assert "about" in user_dict

        # Check sensitive data is available
        assert "apikey" in user_dict
        assert "email" in user_dict

        # Passwords and reset keys should never be available
        assert "password" not in user_dict
        assert "reset_key" not in user_dict

    @pytest.mark.usefixtures("with_request_context")
    def test_24_user_dictize_as_other_user(self):
        """User should not be able to see other's sensitive data."""
        context = {"model": model, "session": model.Session, "user": "annafan"}

        user = model.User.by_name("tester")

        user_dict = user_dictize(user, context)

        # Check some of the non-sensitive data
        assert "name" in user_dict
        assert "about" in user_dict

        # Check sensitive data is not available
        assert "apikey" not in user_dict
        assert "reset_key" not in user_dict
        assert "email" not in user_dict

        # Passwords should never be available
        assert "password" not in user_dict

    def test_25_user_dictize_as_anonymous(self):
        """Anonymous should not be able to see other's sensitive data."""
        context = {"model": model, "session": model.Session, "user": ""}

        user = model.User.by_name("tester")

        user_dict = user_dictize(user, context)

        # Check some of the non-sensitive data
        assert "name" in user_dict
        assert "about" in user_dict

        # Check sensitive data is not available
        assert "apikey" not in user_dict
        assert "reset_key" not in user_dict
        assert "email" not in user_dict

        # Passwords should never be available
        assert "password" not in user_dict
