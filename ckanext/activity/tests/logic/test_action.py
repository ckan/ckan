# -*- coding: utf-8 -*-

import copy
import datetime
import time

import pytest

from ckan import model
import ckan.plugins.toolkit as tk

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

from ckanext.activity.model.activity import Activity, package_activity_list


def _clear_activities():
    from ckan import model

    model.Session.query(Activity).delete()
    model.Session.flush()


def _seconds_since_timestamp(timestamp, format_):
    dt = datetime.datetime.strptime(timestamp, format_)
    now = datetime.datetime.utcnow()
    assert now > dt  # we assume timestamp is not in the future
    return (now - dt).total_seconds()


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("with_plugins")
class TestLimits:
    def test_activity_list_actions(self):
        actions = [
            "user_activity_list",
            "package_activity_list",
            "group_activity_list",
            "organization_activity_list",
            "recently_changed_packages_activity_list",
            "current_package_list_with_resources",
        ]
        for action in actions:
            with pytest.raises(tk.ValidationError):
                helpers.call_action(
                    action,
                    id="test_user",
                    limit="not_an_int",
                    offset="not_an_int",
                )
            with pytest.raises(tk.ValidationError):
                helpers.call_action(
                    action, id="test_user", limit=-1, offset=-1
                )


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestActivityShow:
    def test_simple_with_data(self, package, user, activity_factory):
        activity = activity_factory(
            user_id=user["id"],
            object_id=package["id"],
            activity_type="new package",
            data={"package": copy.deepcopy(package), "actor": "Mr Someone"},
        )
        activity_shown = helpers.call_action(
            "activity_show", id=activity["id"]
        )
        assert activity_shown["user_id"] == user["id"]
        assert (
            _seconds_since_timestamp(
                activity_shown["timestamp"], "%Y-%m-%dT%H:%M:%S.%f"
            )
            < 10
        )
        assert activity_shown["object_id"] == package["id"]
        assert activity_shown["data"] == {
            "package": package,
            "actor": "Mr Someone",
        }
        assert activity_shown["activity_type"] == "new package"


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestPackageActivityList(object):
    def test_create_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]
        assert "extras" in activities[0]["data"]["package"]

    def test_change_dataset(self):
        user = factories.User()
        _clear_activities()
        dataset = factories.Dataset(user=user)
        original_title = dataset["title"]
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package",
            "new package",
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]
        assert (
            activities[0]["data"]["package"]["title"]
            == "Dataset with changed title"
        )

        # the old dataset still has the old title
        assert activities[1]["activity_type"] == "new package"
        assert activities[1]["data"]["package"]["title"] == original_title

    def test_change_dataset_add_extra(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["extras"].append(dict(key="rating", value="great"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]
        assert "extras" in activities[0]["data"]["package"]

    def test_change_dataset_change_extra(self):
        user = factories.User()
        dataset = factories.Dataset(
            user=user, extras=[dict(key="rating", value="great")]
        )
        _clear_activities()
        dataset["extras"][0] = dict(key="rating", value="ok")
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]
        assert "extras" in activities[0]["data"]["package"]

    def test_change_dataset_delete_extra(self):
        user = factories.User()
        dataset = factories.Dataset(
            user=user, extras=[dict(key="rating", value="great")]
        )
        _clear_activities()
        dataset["extras"] = []
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]
        assert "extras" in activities[0]["data"]["package"]

    def test_change_dataset_add_resource(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        factories.Resource(package_id=dataset["id"], user=user)

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]
        # NB the detail is not included - that is only added in by
        # activity_list_to_html()

    def test_change_dataset_change_resource(self):
        user = factories.User()
        dataset = factories.Dataset(
            user=user,
            resources=[dict(url="https://example.com/foo.csv", format="csv")],
        )
        _clear_activities()
        dataset["resources"][0]["format"] = "pdf"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset_delete_resource(self):
        user = factories.User()
        dataset = factories.Dataset(
            user=user,
            resources=[dict(url="https://example.com/foo.csv", format="csv")],
        )
        _clear_activities()
        dataset["resources"] = []
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset_add_tag(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["tags"].append(dict(name="checked"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_delete_tag_from_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user, tags=[dict(name="checked")])
        _clear_activities()
        dataset["tags"] = []
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_delete_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "deleted package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_private_dataset_has_no_activity(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(
            private=True, owner_org=org["id"], user=user
        )
        dataset["tags"] = []
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == []

    def test_private_dataset_delete_has_no_activity(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(
            private=True, owner_org=org["id"], user=user
        )
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == []

    def _create_bulk_types_activities(self, types):
        dataset = factories.Dataset()
        from ckan import model

        user = factories.User()

        objs = [
            Activity(
                user_id=user["id"],
                object_id=dataset["id"],
                activity_type=activity_type,
                data=None,
            )
            for activity_type in types
        ]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return dataset["id"]

    def test_error_bad_search(self):
        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "package_activity_list",
                id=id,
                activity_types=["new package"],
                exclude_activity_types=["deleted package"],
            )

    def test_activity_types_filter(self):
        types = [
            "new package",
            "changed package",
            "deleted package",
            "changed package",
            "new package",
        ]
        id = self._create_bulk_types_activities(types)

        activities_new = helpers.call_action(
            "package_activity_list", id=id, activity_types=["new package"]
        )
        assert len(activities_new) == 2

        activities_not_new = helpers.call_action(
            "package_activity_list",
            id=id,
            exclude_activity_types=["new package"],
        )
        assert len(activities_not_new) == 3

        activities_delete = helpers.call_action(
            "package_activity_list", id=id, activity_types=["deleted package"]
        )
        assert len(activities_delete) == 1

        activities_not_deleted = helpers.call_action(
            "package_activity_list",
            id=id,
            exclude_activity_types=["deleted package"],
        )
        assert len(activities_not_deleted) == 4

    def _create_bulk_package_activities(self, count):
        dataset = factories.Dataset()
        from ckan import model

        user = factories.User()

        objs = [
            Activity(
                user_id=user["id"],
                object_id=dataset["id"],
                activity_type=None,
                data=None,
            )
            for _ in range(count)
        ]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return dataset["id"]

    def test_limit_default(self):
        id = self._create_bulk_package_activities(35)
        results = helpers.call_action("package_activity_list", id=id)
        assert len(results) == 31  # i.e. default value

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    def test_limit_configured(self):
        id = self._create_bulk_package_activities(7)
        results = helpers.call_action("package_activity_list", id=id)
        assert len(results) == 5  # i.e. ckan.activity_list_limit

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    @pytest.mark.ckan_config("ckan.activity_list_limit_max", "7")
    def test_limit_hits_max(self):
        id = self._create_bulk_package_activities(9)
        results = helpers.call_action(
            "package_activity_list", id=id, limit="9"
        )
        assert len(results) == 7  # i.e. ckan.activity_list_limit_max

    def test_normal_user_doesnt_see_hidden_activities(self):
        # activity is 'hidden' because dataset is created by site_user
        dataset = factories.Dataset()

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == []

    def test_sysadmin_user_doesnt_see_hidden_activities_by_default(self):
        # activity is 'hidden' because dataset is created by site_user
        dataset = factories.Dataset()

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        assert [activity["activity_type"] for activity in activities] == []

    def test_sysadmin_user_can_include_hidden_activities(self):
        # activity is 'hidden' because dataset is created by site_user
        dataset = factories.Dataset()

        activities = helpers.call_action(
            "package_activity_list",
            include_hidden_activity=True,
            id=dataset["id"],
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new package"
        ]

    def _create_dataset_with_activities(self, updates: int = 3):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        ctx = {"user": user["name"]}

        for c in range(updates):
            dataset["title"] = "Dataset v{}".format(c)
            helpers.call_action("package_update", context=ctx, **dataset)

        return dataset

    def test_activity_after(self):
        """Test activities after timestamp"""
        dataset = self._create_dataset_with_activities()

        db_activities = package_activity_list(dataset["id"], limit=10)
        pkg_activities = helpers.call_action(
            "package_activity_list",
            id=dataset["id"],
            after=db_activities[2].timestamp.timestamp(),
        )
        # we expect just 2 (the first 2)
        assert len(pkg_activities) == 2
        # first activity here is the first one.
        assert pkg_activities[0]["activity_type"] == "changed package"
        pkg_activity_time = datetime.datetime.fromisoformat(
            pkg_activities[0]["timestamp"]
        )
        assert pkg_activity_time == db_activities[0].timestamp

        # last activity here is the 2nd one.
        assert pkg_activities[1]["activity_type"] == "changed package"
        pkg_activity_time = datetime.datetime.fromisoformat(
            pkg_activities[1]["timestamp"]
        )
        assert pkg_activity_time == db_activities[1].timestamp

    def test_activity_offset(self):
        """Test activities after timestamp"""
        dataset = self._create_dataset_with_activities()

        db_activities = package_activity_list(dataset["id"], limit=10)
        pkg_activities = helpers.call_action(
            "package_activity_list", id=dataset["id"], offset=2
        )
        # we expect just 2 (the last 2)
        assert len(pkg_activities) == 2
        # first activity here is the first one.
        assert pkg_activities[0]["activity_type"] == "changed package"
        pkg_activity_time = datetime.datetime.fromisoformat(
            pkg_activities[0]["timestamp"]
        )
        assert pkg_activity_time == db_activities[2].timestamp

        # last activity here is the package creation.
        assert pkg_activities[1]["activity_type"] == "new package"
        pkg_activity_time = datetime.datetime.fromisoformat(
            pkg_activities[1]["timestamp"]
        )
        assert pkg_activity_time == db_activities[3].timestamp

    def test_activity_before(self):
        """Test activities before timestamp"""
        dataset = self._create_dataset_with_activities()

        db_activities = package_activity_list(dataset["id"], limit=10)
        pkg_activities = helpers.call_action(
            "package_activity_list",
            id=dataset["id"],
            before=db_activities[1].timestamp.timestamp(),
        )
        # we expect just 2 (the last 2)
        assert len(pkg_activities) == 2
        # first activity here is the first one.
        assert pkg_activities[0]["activity_type"] == "changed package"
        pkg_activity_time = datetime.datetime.fromisoformat(
            pkg_activities[0]["timestamp"]
        )
        assert pkg_activity_time == db_activities[2].timestamp

        # last activity here is the package creation.
        assert pkg_activities[-1]["activity_type"] == "new package"
        pkg_activity_time = datetime.datetime.fromisoformat(
            pkg_activities[-1]["timestamp"]
        )
        assert pkg_activity_time == db_activities[3].timestamp

    def test_activity_after_before(self):
        """Test activities before timestamp"""
        dataset = self._create_dataset_with_activities()

        db_activities = package_activity_list(dataset["id"], limit=10)
        pkg_activities = helpers.call_action(
            "package_activity_list",
            id=dataset["id"],
            before=db_activities[1].timestamp.timestamp(),
            after=db_activities[3].timestamp.timestamp(),
        )
        # we expect just 1 (db_activities[2])
        assert len(pkg_activities) == 1
        # first activity here is the first one.
        assert pkg_activities[0]["activity_type"] == "changed package"
        pkg_activity_time = datetime.datetime.fromisoformat(
            pkg_activities[0]["timestamp"]
        )
        assert pkg_activity_time == db_activities[2].timestamp

    def test_activity_after_before_offset(self):
        """Test activities before timestamp"""
        dataset = self._create_dataset_with_activities(updates=4)

        db_activities = package_activity_list(dataset["id"], limit=10)
        pkg_activities = helpers.call_action(
            "package_activity_list",
            id=dataset["id"],
            before=db_activities[1].timestamp.timestamp(),
            after=db_activities[4].timestamp.timestamp(),
            offset=1,
        )
        # we expect just 1 (db_activities[3])
        assert len(pkg_activities) == 1
        # first activity here is the first one.
        assert pkg_activities[0]["activity_type"] == "changed package"
        pkg_activity_time = datetime.datetime.fromisoformat(
            pkg_activities[0]["timestamp"]
        )
        assert pkg_activity_time == db_activities[3].timestamp


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestUserActivityList(object):
    def test_create_user(self):
        user = factories.User()

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "new user"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == user["id"]

    def test_user_update_activity_stream(self):
        """Test that the right activity is emitted when updating a user."""

        user = factories.User()
        before = datetime.datetime.utcnow()

        # FIXME we have to pass the email address and password to user_update
        # even though we're not updating those fields, otherwise validation
        # fails.
        helpers.call_action(
            "user_update",
            id=user["id"],
            name=user["name"],
            email=user["email"],
            password=factories.User.stub().password,
            fullname="updated full name",
        )

        activity_stream = helpers.call_action(
            "user_activity_list", id=user["id"]
        )
        latest_activity = activity_stream[0]
        assert latest_activity["activity_type"] == "changed user"
        assert latest_activity["object_id"] == user["id"]
        assert latest_activity["user_id"] == user["id"]
        after = datetime.datetime.utcnow()
        timestamp = datetime.datetime.strptime(
            latest_activity["timestamp"], "%Y-%m-%dT%H:%M:%S.%f"
        )
        assert timestamp >= before and timestamp <= after

    def test_create_dataset(self):
        user = factories.User()
        _clear_activities()
        dataset = factories.Dataset(user=user)

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "new package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_dataset_changed_by_another_user(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["extras"].append(dict(key="rating", value="great"))
        helpers.call_action(
            "package_update", context={"user": another_user["name"]}, **dataset
        )

        # the user might have created the dataset, but a change by another
        # user does not show on the user's activity stream
        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == []

    def test_change_dataset_add_extra(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["extras"].append(dict(key="rating", value="great"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset_add_tag(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["tags"].append(dict(name="checked"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_create_group(self):
        user = factories.User()
        _clear_activities()
        group = factories.Group(user=user)

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "new group"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == group["id"]
        assert activities[0]["data"]["group"]["title"] == group["title"]

    def test_delete_group_using_group_delete(self):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        helpers.call_action(
            "group_delete", context={"user": user["name"]}, **group
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "deleted group"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == group["id"]
        assert activities[0]["data"]["group"]["title"] == group["title"]

    def test_delete_group_by_updating_state(self):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        group["state"] = "deleted"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "deleted group"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == group["id"]
        assert activities[0]["data"]["group"]["title"] == group["title"]

    def test_create_organization(self):
        user = factories.User()
        _clear_activities()
        org = factories.Organization(user=user)

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "new organization"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == org["id"]
        assert activities[0]["data"]["group"]["title"] == org["title"]

    def test_delete_org_using_organization_delete(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        helpers.call_action(
            "organization_delete", context={"user": user["name"]}, **org
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "deleted organization"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == org["id"]
        assert activities[0]["data"]["group"]["title"] == org["title"]

    def test_delete_org_by_updating_state(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        org["state"] = "deleted"
        helpers.call_action(
            "organization_update", context={"user": user["name"]}, **org
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "deleted organization"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == org["id"]
        assert activities[0]["data"]["group"]["title"] == org["title"]

    def _create_bulk_user_activities(self, count):
        from ckan import model

        user = factories.User()

        objs = [
            Activity(
                user_id=user["id"],
                object_id=None,
                activity_type=None,
                data=None,
            )
            for _ in range(count)
        ]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return user["id"]

    def test_limit_default(self):
        id = self._create_bulk_user_activities(35)
        results = helpers.call_action("user_activity_list", id=id)
        assert len(results) == 31  # i.e. default value

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    def test_limit_configured(self):
        id = self._create_bulk_user_activities(7)
        results = helpers.call_action("user_activity_list", id=id)
        assert len(results) == 5  # i.e. ckan.activity_list_limit

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    @pytest.mark.ckan_config("ckan.activity_list_limit_max", "7")
    def test_limit_hits_max(self):
        id = self._create_bulk_user_activities(9)
        results = helpers.call_action("user_activity_list", id=id, limit="9")
        assert len(results) == 7  # i.e. ckan.activity_list_limit_max


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestGroupActivityList(object):
    def test_create_group(self):
        user = factories.User()
        group = factories.Group(user=user)

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "new group"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == group["id"]
        assert activities[0]["data"]["group"]["title"] == group["title"]

    def test_change_group(self):
        user = factories.User()
        _clear_activities()
        group = factories.Group(user=user)
        original_title = group["title"]
        group["title"] = "Group with changed title"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "changed group",
            "new group",
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == group["id"]
        assert (
            activities[0]["data"]["group"]["title"]
            == "Group with changed title"
        )

        # the old group still has the old title
        assert activities[1]["activity_type"] == "new group"
        assert activities[1]["data"]["group"]["title"] == original_title

    def test_create_dataset(self):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "new package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset(self):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)
        original_title = dataset["title"]
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "changed package",
            "new package",
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

        # the old dataset still has the old title
        assert activities[1]["activity_type"] == "new package"
        assert activities[1]["data"]["package"]["title"] == original_title

    def test_change_dataset_add_extra(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)
        _clear_activities()
        dataset["extras"].append(dict(key="rating", value="great"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset_add_tag(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)
        _clear_activities()
        dataset["tags"].append(dict(name="checked"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_delete_dataset(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "deleted package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset_that_used_to_be_in_the_group(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)
        # remove the dataset from the group
        dataset["groups"] = []
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )
        _clear_activities()
        # edit the dataset
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        # dataset change should not show up in its former group
        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == []

    def test_delete_dataset_that_used_to_be_in_the_group(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)
        # remove the dataset from the group
        dataset["groups"] = []
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        # NOTE:
        # ideally the dataset's deletion would not show up in its old group
        # but it can't be helped without _group_activity_query getting very
        # complicated
        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == [
            "deleted package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def _create_bulk_group_activities(self, count):
        group = factories.Group()
        from ckan import model

        user = factories.User()

        objs = [
            Activity(
                user_id=user["id"],
                object_id=group["id"],
                activity_type=None,
                data=None,
            )
            for _ in range(count)
        ]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return group["id"]

    def test_limit_default(self):
        id = self._create_bulk_group_activities(35)
        results = helpers.call_action("group_activity_list", id=id)
        assert len(results) == 31  # i.e. default value

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    def test_limit_configured(self):
        id = self._create_bulk_group_activities(7)
        results = helpers.call_action("group_activity_list", id=id)
        assert len(results) == 5  # i.e. ckan.activity_list_limit

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    @pytest.mark.ckan_config("ckan.activity_list_limit_max", "7")
    def test_limit_hits_max(self):
        id = self._create_bulk_group_activities(9)
        results = helpers.call_action("group_activity_list", id=id, limit="9")
        assert len(results) == 7  # i.e. ckan.activity_list_limit_max

    def test_normal_user_doesnt_see_hidden_activities(self):
        # activity is 'hidden' because group is created by site_user
        group = factories.Group()

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == []

    def test_sysadmin_user_doesnt_see_hidden_activities_by_default(self):
        # activity is 'hidden' because group is created by site_user
        group = factories.Group()

        activities = helpers.call_action("group_activity_list", id=group["id"])
        assert [activity["activity_type"] for activity in activities] == []

    def test_sysadmin_user_can_include_hidden_activities(self):
        # activity is 'hidden' because group is created by site_user
        group = factories.Group()

        activities = helpers.call_action(
            "group_activity_list", include_hidden_activity=True, id=group["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new group"
        ]


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestOrganizationActivityList(object):
    def test_bulk_make_public(self):
        org = factories.Organization()

        dataset1 = factories.Dataset(owner_org=org["id"], private=True)
        dataset2 = factories.Dataset(owner_org=org["id"], private=True)

        helpers.call_action(
            "bulk_update_public",
            {},
            datasets=[dataset1["id"], dataset2["id"]],
            org_id=org["id"],
        )
        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert activities[0]["activity_type"] == "changed package"

    def test_bulk_delete(self):
        org = factories.Organization()

        dataset1 = factories.Dataset(owner_org=org["id"])
        dataset2 = factories.Dataset(owner_org=org["id"])

        helpers.call_action(
            "bulk_update_delete",
            {},
            datasets=[dataset1["id"], dataset2["id"]],
            org_id=org["id"],
        )

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert activities[0]["activity_type"] == "deleted package"

    def test_create_organization(self):
        user = factories.User()
        org = factories.Organization(user=user)

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new organization"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == org["id"]
        assert activities[0]["data"]["group"]["title"] == org["title"]

    def test_change_organization(self):
        user = factories.User()
        _clear_activities()
        org = factories.Organization(user=user)
        original_title = org["title"]
        org["title"] = "Organization with changed title"
        helpers.call_action(
            "organization_update", context={"user": user["name"]}, **org
        )

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed organization",
            "new organization",
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == org["id"]
        assert (
            activities[0]["data"]["group"]["title"]
            == "Organization with changed title"
        )

        # the old org still has the old title
        assert activities[1]["activity_type"] == "new organization"
        assert activities[1]["data"]["group"]["title"] == original_title

    def test_create_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(owner_org=org["id"], user=user)

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        original_title = dataset["title"]
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package",
            "new package",
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

        # the old dataset still has the old title
        assert activities[1]["activity_type"] == "new package"
        assert activities[1]["data"]["package"]["title"] == original_title

    def test_change_dataset_add_tag(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        _clear_activities()
        dataset["tags"].append(dict(name="checked"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_delete_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "deleted package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset_that_used_to_be_in_the_org(self):
        user = factories.User()
        org = factories.Organization(user=user)
        org2 = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        # remove the dataset from the org
        dataset["owner_org"] = org2["id"]
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )
        _clear_activities()
        # edit the dataset
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        # dataset change should not show up in its former group
        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == []

    def test_delete_dataset_that_used_to_be_in_the_org(self):
        user = factories.User()
        org = factories.Organization(user=user)
        org2 = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        # remove the dataset from the group
        dataset["owner_org"] = org2["id"]
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )
        _clear_activities()
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        # dataset deletion should not show up in its former org
        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == []

    def _create_bulk_org_activities(self, count):
        org = factories.Organization()
        from ckan import model

        user = factories.User()

        objs = [
            Activity(
                user_id=user["id"],
                object_id=org["id"],
                activity_type=None,
                data=None,
            )
            for _ in range(count)
        ]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return org["id"]

    def test_limit_default(self):
        id = self._create_bulk_org_activities(35)
        results = helpers.call_action("organization_activity_list", id=id)
        assert len(results) == 31  # i.e. default value

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    def test_limit_configured(self):
        id = self._create_bulk_org_activities(7)
        results = helpers.call_action("organization_activity_list", id=id)
        assert len(results) == 5  # i.e. ckan.activity_list_limit

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    @pytest.mark.ckan_config("ckan.activity_list_limit_max", "7")
    def test_limit_hits_max(self):
        id = self._create_bulk_org_activities(9)
        results = helpers.call_action(
            "organization_activity_list", id=id, limit="9"
        )
        assert len(results) == 7  # i.e. ckan.activity_list_limit_max

    def test_normal_user_doesnt_see_hidden_activities(self):
        # activity is 'hidden' because org is created by site_user
        org = factories.Organization()

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == []

    def test_sysadmin_user_doesnt_see_hidden_activities_by_default(self):
        # activity is 'hidden' because org is created by site_user
        org = factories.Organization()

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == []

    def test_sysadmin_user_can_include_hidden_activities(self):
        # activity is 'hidden' because org is created by site_user
        org = factories.Organization()

        activities = helpers.call_action(
            "organization_activity_list",
            include_hidden_activity=True,
            id=org["id"],
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new organization"
        ]


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestRecentlyChangedPackagesActivityList:
    def test_create_dataset(self):
        user = factories.User()
        org = factories.Dataset(user=user)

        activities = helpers.call_action(
            "recently_changed_packages_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == org["id"]
        assert activities[0]["data"]["package"]["title"] == org["title"]

    def test_change_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        original_title = dataset["title"]
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "recently_changed_packages_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package",
            "new package",
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

        # the old dataset still has the old title
        assert activities[1]["activity_type"] == "new package"
        assert activities[1]["data"]["package"]["title"] == original_title

    def test_change_dataset_add_extra(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        _clear_activities()
        dataset["extras"].append(dict(key="rating", value="great"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "recently_changed_packages_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_change_dataset_add_tag(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        _clear_activities()
        dataset["tags"].append(dict(name="checked"))
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "recently_changed_packages_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "changed package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def test_delete_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "organization_activity_list", id=org["id"]
        )
        assert [activity["activity_type"] for activity in activities] == [
            "deleted package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]

    def _create_bulk_package_activities(self, count):
        from ckan import model

        user = factories.User()

        objs = [
            Activity(
                user_id=user["id"],
                object_id=None,
                activity_type="new_package",
                data=None,
            )
            for _ in range(count)
        ]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()

    def test_limit_default(self):
        self._create_bulk_package_activities(35)
        results = helpers.call_action(
            "recently_changed_packages_activity_list"
        )
        assert len(results) == 31  # i.e. default value

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    def test_limit_configured(self):
        self._create_bulk_package_activities(7)
        results = helpers.call_action(
            "recently_changed_packages_activity_list"
        )
        assert len(results) == 5  # i.e. ckan.activity_list_limit

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    @pytest.mark.ckan_config("ckan.activity_list_limit_max", "7")
    def test_limit_hits_max(self):
        self._create_bulk_package_activities(9)
        results = helpers.call_action(
            "recently_changed_packages_activity_list", limit="9"
        )
        assert len(results) == 7  # i.e. ckan.activity_list_limit_max


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestDashboardActivityList(object):
    def test_create_user(self):
        user = factories.User()

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new user"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == user["id"]
        # user's own activities are always marked ``'is_new': False``
        assert not activities[0]["is_new"]

    def test_create_dataset(self):
        user = factories.User()
        _clear_activities()
        dataset = factories.Dataset(user=user)

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new package"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == dataset["id"]
        assert activities[0]["data"]["package"]["title"] == dataset["title"]
        # user's own activities are always marked ``'is_new': False``
        assert not activities[0]["is_new"]

    def test_create_group(self):
        user = factories.User()
        _clear_activities()
        group = factories.Group(user=user)

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new group"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == group["id"]
        assert activities[0]["data"]["group"]["title"] == group["title"]
        # user's own activities are always marked ``'is_new': False``
        assert not activities[0]["is_new"]

    def test_create_organization(self):
        user = factories.User()
        _clear_activities()
        org = factories.Organization(user=user)

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [activity["activity_type"] for activity in activities] == [
            "new organization"
        ]
        assert activities[0]["user_id"] == user["id"]
        assert activities[0]["object_id"] == org["id"]
        assert activities[0]["data"]["group"]["title"] == org["title"]
        # user's own activities are always marked ``'is_new': False``
        assert not activities[0]["is_new"]

    def _create_bulk_package_activities(self, count):
        user = factories.User()
        from ckan import model

        objs = [
            Activity(
                user_id=user["id"],
                object_id=None,
                activity_type=None,
                data=None,
            )
            for _ in range(count)
        ]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return user["id"]

    def test_limit_default(self):
        id = self._create_bulk_package_activities(35)
        results = helpers.call_action(
            "dashboard_activity_list", context={"user": id}
        )
        assert len(results) == 31  # i.e. default value

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    def test_limit_configured(self):
        id = self._create_bulk_package_activities(7)
        results = helpers.call_action(
            "dashboard_activity_list", context={"user": id}
        )
        assert len(results) == 5  # i.e. ckan.activity_list_limit

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    @pytest.mark.ckan_config("ckan.activity_list_limit_max", "7")
    def test_limit_hits_max(self):
        id = self._create_bulk_package_activities(9)
        results = helpers.call_action(
            "dashboard_activity_list", limit="9", context={"user": id}
        )
        assert len(results) == 7  # i.e. ckan.activity_list_limit_max


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestDashboardNewActivities(object):
    def test_users_own_activities(self):
        # a user's own activities are not shown as "new"
        user = factories.User()
        dataset = factories.Dataset(user=user)
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )
        group = factories.Group(user=user)
        group["title"] = "Group with changed title"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )
        helpers.call_action(
            "group_delete", context={"user": user["name"]}, **group
        )

        new_activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [activity["is_new"] for activity in new_activities] == [
            False
        ] * 7
        new_activities_count = helpers.call_action(
            "dashboard_new_activities_count", context={"user": user["id"]}
        )
        assert new_activities_count == 0

    def test_activities_by_a_followed_user(self):
        user = factories.User()
        followed_user = factories.User()
        helpers.call_action(
            "follow_user", context={"user": user["name"]}, **followed_user
        )
        _clear_activities()
        dataset = factories.Dataset(user=followed_user)
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update",
            context={"user": followed_user["name"]},
            **dataset,
        )
        helpers.call_action(
            "package_delete",
            context={"user": followed_user["name"]},
            **dataset,
        )
        group = factories.Group(user=followed_user)
        group["title"] = "Group with changed title"
        helpers.call_action(
            "group_update", context={"user": followed_user["name"]}, **group
        )
        helpers.call_action(
            "group_delete", context={"user": followed_user["name"]}, **group
        )

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            activity["activity_type"] for activity in activities[::-1]
        ] == [
            "new package",
            "changed package",
            "deleted package",
            "new group",
            "changed group",
            "deleted group",
        ]
        assert [activity["is_new"] for activity in activities] == [True] * 6
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 6
        )

    def test_activities_on_a_followed_dataset(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        _clear_activities()
        dataset = factories.Dataset(user=another_user)
        helpers.call_action(
            "follow_dataset", context={"user": user["name"]}, **dataset
        )
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": another_user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == [
            ("new package", True),
            # NB The 'new package' activity is in our activity stream and shows
            # as "new" even though it occurred before we followed it. This is
            # known & intended design.
            ("changed package", True),
        ]
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 2
        )

    def test_activities_on_a_followed_group(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        _clear_activities()
        group = factories.Group(user=user)
        helpers.call_action(
            "follow_group", context={"user": user["name"]}, **group
        )
        group["title"] = "Group with changed title"
        helpers.call_action(
            "group_update", context={"user": another_user["name"]}, **group
        )

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == [
            ("new group", False),  # False because user did this one herself
            ("changed group", True),
        ]
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 1
        )

    def test_activities_on_a_dataset_in_a_followed_group(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        group = factories.Group(user=user)
        helpers.call_action(
            "follow_group", context={"user": user["name"]}, **group
        )
        _clear_activities()
        dataset = factories.Dataset(
            groups=[{"name": group["name"]}], user=another_user
        )
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": another_user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == [("new package", True), ("changed package", True)]
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 2
        )

    def test_activities_on_a_dataset_in_a_followed_org(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        org = factories.Organization(user=user)
        helpers.call_action(
            "follow_group", context={"user": user["name"]}, **org
        )
        _clear_activities()
        dataset = factories.Dataset(owner_org=org["id"], user=another_user)
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": another_user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == [("new package", True), ("changed package", True)]
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 2
        )

    def test_activities_that_should_not_show(self):
        user = factories.User()
        _clear_activities()
        # another_user does some activity unconnected with user
        another_user = factories.Sysadmin()
        group = factories.Group(user=another_user)
        dataset = factories.Dataset(
            groups=[{"name": group["name"]}], user=another_user
        )
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": another_user["name"]}, **dataset
        )

        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == []
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 0
        )

    @pytest.mark.ckan_config("ckan.activity_list_limit", "5")
    def test_maximum_number_of_new_activities(self):
        """Test that the new activities count does not go higher than 5, even
        if there are more than 5 new activities from the user's followers."""
        user = factories.User()
        another_user = factories.Sysadmin()
        dataset = factories.Dataset()
        helpers.call_action(
            "follow_dataset", context={"user": user["name"]}, **dataset
        )
        for n in range(0, 7):
            dataset["notes"] = "Updated {n} times".format(n=n)
            helpers.call_action(
                "package_update",
                context={"user": another_user["name"]},
                **dataset,
            )
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 5
        )


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_request_context", "with_plugins")
class TestSendEmailNotifications(object):
    # TODO: this action doesn't do much. Maybe it well be better to move tests
    # into lib.email_notifications eventually

    def check_email(self, email, address, name, subject):
        assert email[1] == "info@test.ckan.net"
        assert email[2] == [address]
        assert subject in email[3]
        # TODO: Check that body contains link to dashboard and email prefs.

    def test_fresh_setupnotifications(self, mail_server):
        helpers.call_action("send_email_notifications")
        assert (
            len(mail_server.get_smtp_messages()) == 0
        ), "Notification came out of nowhere"

    def test_single_notification(self, mail_server):
        pkg = factories.Dataset()
        user = factories.User(activity_streams_email_notifications=True)
        helpers.call_action(
            "follow_dataset", {"user": user["name"]}, id=pkg["id"]
        )
        helpers.call_action("package_update", id=pkg["id"], notes="updated")
        helpers.call_action("send_email_notifications")
        messages = mail_server.get_smtp_messages()
        assert len(messages) == 1
        self.check_email(
            messages[0],
            user["email"],
            user["name"],
            "1 new activity from CKAN",
        )

    def test_multiple_notifications(self, mail_server):
        pkg = factories.Dataset()
        user = factories.User(activity_streams_email_notifications=True)
        helpers.call_action(
            "follow_dataset", {"user": user["name"]}, id=pkg["id"]
        )
        for i in range(3):
            helpers.call_action(
                "package_update", id=pkg["id"], notes=f"updated {i} times"
            )
        helpers.call_action("send_email_notifications")
        messages = mail_server.get_smtp_messages()
        assert len(messages) == 1
        self.check_email(
            messages[0],
            user["email"],
            user["name"],
            "3 new activities from CKAN",
        )

    def test_no_notifications_if_dashboard_visited(self, mail_server):
        pkg = factories.Dataset()
        user = factories.User(activity_streams_email_notifications=True)
        helpers.call_action(
            "follow_dataset", {"user": user["name"]}, id=pkg["id"]
        )
        helpers.call_action("package_update", id=pkg["id"], notes="updated")
        new_activities_count = helpers.call_action(
            "dashboard_new_activities_count",
            {"user": user["name"]},
            id=pkg["id"],
        )
        assert new_activities_count == 1

        helpers.call_action(
            "dashboard_mark_activities_old",
            {"user": user["name"]},
            id=pkg["id"],
        )
        helpers.call_action("send_email_notifications")
        messages = mail_server.get_smtp_messages()
        assert len(messages) == 0

    def test_notifications_disabled_by_default(self):
        user = factories.User()
        assert not user["activity_streams_email_notifications"]

    def test_no_emails_when_notifications_disabled(self, mail_server):
        pkg = factories.Dataset()
        user = factories.User()
        helpers.call_action(
            "follow_dataset", {"user": user["name"]}, id=pkg["id"]
        )
        helpers.call_action("package_update", id=pkg["id"], notes="updated")
        helpers.call_action("send_email_notifications")
        messages = mail_server.get_smtp_messages()
        assert len(messages) == 0
        new_activities_count = helpers.call_action(
            "dashboard_new_activities_count",
            {"user": user["name"]},
            id=pkg["id"],
        )
        assert new_activities_count == 1

    @pytest.mark.ckan_config(
        "ckan.activity_streams_email_notifications", False
    )
    def test_send_email_notifications_feature_disabled(self, mail_server):
        with pytest.raises(tk.ValidationError):
            helpers.call_action("send_email_notifications")
        messages = mail_server.get_smtp_messages()
        assert len(messages) == 0

    @pytest.mark.ckan_config("ckan.email_notifications_since", ".000001")
    def test_email_notifications_since(self, mail_server):
        pkg = factories.Dataset()
        user = factories.User(activity_streams_email_notifications=True)
        helpers.call_action(
            "follow_dataset", {"user": user["name"]}, id=pkg["id"]
        )
        helpers.call_action("package_update", id=pkg["id"], notes="updated")
        time.sleep(0.01)
        helpers.call_action("send_email_notifications")
        messages = mail_server.get_smtp_messages()
        assert len(messages) == 0


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestDashboardMarkActivitiesOld(object):
    def test_mark_as_old_some_activities_by_a_followed_user(self):
        # do some activity that will show up on user's dashboard
        user = factories.User()
        # now some activity that is "new" because it is by a followed user
        followed_user = factories.User()
        helpers.call_action(
            "follow_user", context={"user": user["name"]}, **followed_user
        )
        dataset = factories.Dataset(user=followed_user)
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update",
            context={"user": followed_user["name"]},
            **dataset,
        )
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 3
        )
        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == [
            ("new user", False),
            ("new user", True),
            ("new package", True),
            ("changed package", True),
        ]

        helpers.call_action(
            "dashboard_mark_activities_old", context={"user": user["name"]}
        )

        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 0
        )
        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == [
            ("new user", False),
            ("new user", False),
            ("new package", False),
            ("changed package", False),
        ]


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestFollow:
    @pytest.mark.usefixtures("app")
    def test_follow_dataset_no_activity(self):
        user = factories.User()
        dataset = factories.Dataset()
        _clear_activities()
        helpers.call_action(
            "follow_dataset", context={"user": user["name"]}, id=dataset["id"]
        )
        assert not helpers.call_action("user_activity_list", id=user["id"])

    @pytest.mark.usefixtures("app")
    def test_follow_group_no_activity(self):
        user = factories.User()
        group = factories.Group()
        _clear_activities()
        helpers.call_action(
            "follow_group", context={"user": user["name"]}, **group
        )
        assert not helpers.call_action("user_activity_list", id=user["id"])

    @pytest.mark.usefixtures("app")
    def test_follow_organization_no_activity(self):
        user = factories.User()
        org = factories.Organization()
        _clear_activities()
        helpers.call_action(
            "follow_group", context={"user": user["name"]}, **org
        )
        assert not helpers.call_action("user_activity_list", id=user["id"])

    @pytest.mark.usefixtures("app")
    def test_follow_user_no_activity(self):
        user = factories.User()
        user2 = factories.User()
        _clear_activities()
        helpers.call_action(
            "follow_user", context={"user": user["name"]}, **user2
        )
        assert not helpers.call_action("user_activity_list", id=user["id"])


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestDeferCommitOnCreate(object):

    def test_package_create_defer_commit(self):
        dataset_dict = {
            "name": "test_dataset",
        }
        context = {
            "defer_commit": True,
            "user": factories.User()["name"],
        }

        helpers.call_action("package_create", context=context, **dataset_dict)

        model.Session.close()

        with pytest.raises(tk.ObjectNotFound):
            helpers.call_action("package_show", id=dataset_dict["name"])

        assert model.Session.query(Activity).filter(
            Activity.activity_type != "new user").count() == 0

    def test_group_create_defer_commit(self):
        group_dict = {
            "name": "test_group",
        }
        context = {
            "defer_commit": True,
            "user": factories.User()["name"],
        }

        helpers.call_action("group_create", context=context, **group_dict)

        model.Session.close()

        with pytest.raises(tk.ObjectNotFound):
            helpers.call_action("group_show", id=group_dict["name"])

        assert model.Session.query(Activity).filter(
            Activity.activity_type != "new user").count() == 0

    def test_organization_create_defer_commit(self):
        organization_dict = {
            "name": "test_org",
        }
        context = {
            "defer_commit": True,
            "user": factories.User()["name"],
        }

        helpers.call_action("organization_create", context=context, **organization_dict)

        model.Session.close()

        with pytest.raises(tk.ObjectNotFound):
            helpers.call_action("organization_show", id=organization_dict["name"])

        assert model.Session.query(Activity).filter(
            Activity.activity_type != "new user").count() == 0

    def test_user_create_defer_commit(self):
        stub = factories.User.stub()
        user_dict = {
            "name": stub.name,
            "email": stub.email,
            "password": "test1234",
        }
        context = {"defer_commit": True}

        helpers.call_action("user_create", context=context, **user_dict)

        model.Session.close()

        with pytest.raises(tk.ObjectNotFound):
            helpers.call_action("user_show", id=user_dict["name"])

        assert model.Session.query(Activity).count() == 0
