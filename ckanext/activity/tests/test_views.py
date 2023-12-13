# -*- coding: utf-8 -*-

import unittest.mock as mock
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

import ckan.model as model
import ckan.lib.dictization as dictization
from ckan.lib.helpers import url_for

from ckan.tests import factories, helpers
from ckanext.activity.model import Activity, activity as activity_model
from ckanext.activity.logic.validators import object_id_validators


def _clear_activities():
    model.Session.query(Activity).delete()
    model.Session.flush()


def assert_user_link_in_response(user, response):
    assert (
        '<a href="/user/{}">{}'.format(user["name"], user["fullname"])
        in response
    )


def assert_group_link_in_response(group, response):
    assert (
        '<a href="/{0}/{1}" title="{2}">{2}'.format(group["type"], group["name"], group["title"])
        in response
    )


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestOrganization(object):
    def test_simple(self, app):
        """Checking the template shows the activity stream."""
        user = factories.User()
        org = factories.Organization(user=user)

        url = url_for("activity.organization_activity", id=org["id"])
        response = app.get(url)
        assert user["fullname"] in response
        assert "created the organization" in response

    def test_create_organization(self, app):
        user = factories.User()
        org = factories.Organization(user=user)

        url = url_for("activity.organization_activity", id=org["id"])
        response = app.get(url)
        assert_user_link_in_response(user, response)
        assert "created the organization" in response
        assert_group_link_in_response(org, response)

    def test_change_organization(self, app):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        org["title"] = "Organization with changed title"
        helpers.call_action(
            "organization_update", context={"user": user["name"]}, **org
        )

        url = url_for("activity.organization_activity", id=org["id"])
        response = app.get(url)
        assert_user_link_in_response(user, response)
        assert "updated the organization" in response
        assert_group_link_in_response(org, response)

    def test_delete_org_using_organization_delete(self, app):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        helpers.call_action(
            "organization_delete", context={"user": user["name"]}, **org
        )

        url = url_for("activity.organization_activity", id=org["id"])
        env = {"REMOTE_USER": user["name"]}
        app.get(url, extra_environ=env, status=404)
        # organization_delete causes the Member to state=deleted and then the
        # user doesn't have permission to see their own deleted Organization.
        # Therefore you can't render the activity stream of that org. You'd
        # hope that organization_delete was the same as organization_update
        # state=deleted but they are not...

    def test_delete_org_by_updating_state(self, app):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        org["state"] = "deleted"
        helpers.call_action(
            "organization_update", context={"user": user["name"]}, **org
        )

        url = url_for("activity.organization_activity", id=org["id"])
        env = {"REMOTE_USER": user["name"]}
        response = app.get(url, extra_environ=env)
        assert_user_link_in_response(user, response)
        assert "deleted the organization" in response
        assert_group_link_in_response(org, response)

    def test_create_dataset(self, app):
        user = factories.User()
        org = factories.Organization()
        _clear_activities()
        dataset = factories.Dataset(owner_org=org["id"], user=user)

        url = url_for("activity.organization_activity", id=org["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "created the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_change_dataset(self, app):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        _clear_activities()
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.organization_activity", id=org["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_delete_dataset(self, app):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.organization_activity", id=org["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "deleted the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestUser:
    def test_simple(self, app):
        """Checking the template shows the activity stream."""

        user = factories.User()

        url = url_for("activity.user_activity", id=user["id"])
        response = app.get(url)
        assert user["fullname"] in response
        assert "signed up" in response

    def test_create_user(self, app):

        user = factories.User()

        url = url_for("activity.user_activity", id=user["id"])
        response = app.get(url)
        assert_user_link_in_response(user, response)
        assert "signed up" in response

    def test_change_user(self, app):

        user = factories.User()
        _clear_activities()
        user["fullname"] = "Mr. Changed Name"
        helpers.call_action(
            "user_update", context={"user": user["name"]}, **user
        )

        url = url_for("activity.user_activity", id=user["id"])
        response = app.get(url)
        assert_user_link_in_response(user, response)
        assert "updated their profile" in response

    def test_create_dataset(self, app):

        user = factories.User()
        _clear_activities()
        dataset = factories.Dataset(user=user)

        url = url_for("activity.user_activity", id=user["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "created the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_change_dataset(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.user_activity", id=user["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")

        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_delete_dataset(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.user_activity", id=user["id"])
        env = {"REMOTE_USER": user["name"]}
        response = app.get(url, extra_environ=env)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "deleted the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_create_group(self, app):

        user = factories.User()
        group = factories.Group(user=user)

        url = url_for("activity.user_activity", id=user["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".group")

        assert_user_link_in_response(user, response)
        assert "created the group" in response
        assert group["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert group["title"] in href.text.strip()

    def test_change_group(self, app):

        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        group["title"] = "Group with changed title"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )

        url = url_for("activity.user_activity", id=user["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".group")
        assert_user_link_in_response(user, response)
        assert "updated the group" in response
        assert group["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert group["title"] in href.text.strip()

    def test_delete_group_using_group_delete(self, app):

        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        helpers.call_action(
            "group_delete", context={"user": user["name"]}, **group
        )

        url = url_for("activity.user_activity", id=user["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".group")
        assert_user_link_in_response(user, response)
        assert "deleted the group" in response
        assert group["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert group["title"] in href.text.strip()

    def test_delete_group_by_updating_state(self, app):

        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        group["state"] = "deleted"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )

        url = url_for("activity.group_activity", id=group["id"])
        env = {"REMOTE_USER": user["name"]}
        response = app.get(url, extra_environ=env)
        assert_user_link_in_response(user, response)
        assert "deleted the group" in response
        assert_group_link_in_response(group, response)


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestPackage:
    def test_simple(self, app):
        """Checking the template shows the activity stream."""
        user = factories.User()
        dataset = factories.Dataset(user=user)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        assert user["fullname"] in response
        assert "created the dataset" in response

    def test_create_dataset(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")

        assert_user_link_in_response(user, response)
        assert "created the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_change_dataset(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_create_tag_directly(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["tags"] = [{"name": "some_tag"}]
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )

        assert len(activities) == 1

    def test_create_tag(self, app):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["tags"] = [{"name": "some_tag"}]
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )

        assert len(activities) == 1

    def test_create_extra(self, app):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["extras"] = [{"key": "some", "value": "extra"}]
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )

        assert len(activities) == 1

    def test_create_resource(self, app):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        helpers.call_action(
            "resource_create",
            context={"user": user["name"]},
            name="Test resource",
            package_id=dataset["id"],
        )

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")

        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )

        assert len(activities) == 1

    def test_update_resource(self, app):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        resource = factories.Resource(package_id=dataset["id"])
        _clear_activities()

        helpers.call_action(
            "resource_update",
            context={"user": user["name"]},
            id=resource["id"],
            name="Test resource updated",
            package_id=dataset["id"],
        )

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )

        assert len(activities) == 1

    def test_delete_dataset(self, app):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.organization_activity", id=org["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")

        assert_user_link_in_response(user, response)
        assert "deleted the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_admin_can_see_old_versions(self, app):

        user = factories.User()
        env = {"REMOTE_USER": user["name"]}
        dataset = factories.Dataset(user=user)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url, extra_environ=env)
        assert "View this version" in response

    def test_public_cant_see_old_versions(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        assert "View this version" not in response

    def test_admin_can_see_changes(self, app):

        user = factories.User()
        env = {"REMOTE_USER": user["name"]}
        dataset = factories.Dataset()  # activities by system user aren't shown
        dataset["title"] = "Changed"
        helpers.call_action("package_update", **dataset)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url, extra_environ=env)
        assert "Changes" in response

    def test_public_cant_see_changes(self, app):
        dataset = factories.Dataset()  # activities by system user aren't shown
        dataset["title"] = "Changed"
        helpers.call_action("package_update", **dataset)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        assert "Changes" not in response

    # ckanext-canada uses their IActivity to add their custom activity to the
    # list of validators: https://github.com/open-data/ckanext-canada/blob/6870e5bc38a04aa8cef191b5e9eb361f9560872b/ckanext/canada/plugins.py#L596
    # but it's easier here to just hack patch it in
    @mock.patch(
        "ckanext.activity.logic.validators.object_id_validators",
        dict(
            list(object_id_validators.items())
            + [("changed datastore", "package_id_exists")]
        ),
    )
    def test_custom_activity(self, app):
        """Render a custom activity"""

        user = factories.User()
        organization = factories.Organization(
            users=[{"name": user["id"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"], user=user)
        resource = factories.Resource(package_id=dataset["id"])
        _clear_activities()

        # Create a custom Activity object. This one is inspired by:
        # https://github.com/open-data/ckanext-canada/blob/master/ckanext/canada/activity.py
        activity_dict = {
            "user_id": user["id"],
            "object_id": dataset["id"],
            "activity_type": "changed datastore",
            "data": {
                "resource_id": resource["id"],
                "pkg_type": dataset["type"],
                "resource_name": "june-2018",
                "owner_org": organization["name"],
                "count": 5,
            },
        }
        helpers.call_action("activity_create", **activity_dict)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        assert_user_link_in_response(user, response)
        # it renders the activity with fallback.html, since we've not defined
        # changed_datastore.html in this case
        assert "changed datastore" in response

    def test_redirect_also_with_activity_parameter(self, app):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        activity = activity_model.package_activity_list(
            dataset["id"], limit=1, offset=0
        )[0]
        # view as an admin because viewing the old versions of a dataset
        sysadmin = factories.Sysadmin()
        env = {"REMOTE_USER": sysadmin["name"]}
        response = app.get(
            url_for(
                "activity.package_history",
                id=dataset["id"],
                activity_id=activity.id,
            ),
            status=302,
            extra_environ=env,
            follow_redirects=False,
        )
        expected_path = url_for(
            "activity.package_history",
            id=dataset["name"],
            _external=True,
            activity_id=activity.id,
        )
        assert response.headers["location"] == expected_path

    def test_read_dataset_as_it_used_to_be(self, app):
        dataset = factories.Dataset(title="Original title")
        activity = (
            model.Session.query(Activity)
            .filter_by(object_id=dataset["id"])
            .one()
        )
        dataset["title"] = "Changed title"
        helpers.call_action("package_update", **dataset)

        sysadmin = factories.Sysadmin()
        env = {"REMOTE_USER": sysadmin["name"]}
        response = app.get(
            url_for(
                "activity.package_history",
                id=dataset["name"],
                activity_id=activity.id,
            ),
            extra_environ=env,
        )
        assert helpers.body_contains(response, "Original title")

    def test_read_dataset_as_it_used_to_be_but_is_unmigrated(self, app):
        # Renders the dataset using the activity detail, when that Activity was
        # created with an earlier version of CKAN, and it has not been migrated
        # (with migrate_package_activity.py), which should give a 404

        user = factories.User()
        dataset = factories.Dataset(user=user)

        # delete the modern Activity object that's been automatically created
        modern_activity = (
            model.Session.query(Activity)
            .filter_by(object_id=dataset["id"])
            .one()
        )
        modern_activity.delete()

        # Create an Activity object as it was in earlier versions of CKAN.
        # This code is based on:
        # https://github.com/ckan/ckan/blob/b348bf2fe68db6704ea0a3e22d533ded3d8d4344/ckan/model/package.py#L508
        activity_type = "changed"
        dataset_table_dict = dictization.table_dictize(
            model.Package.get(dataset["id"]), context={"model": model}
        )
        activity = Activity(
            user_id=user["id"],
            object_id=dataset["id"],
            activity_type="%s package" % activity_type,
            data={
                # "actor": a legacy activity had no "actor"
                # "package": a legacy activity had just the package table,
                # rather than the result of package_show
                "package": dataset_table_dict
            },
        )
        model.Session.add(activity)

        sysadmin = factories.Sysadmin()
        env = {"REMOTE_USER": sysadmin["name"]}
        app.get(
            url_for(
                "activity.package_history",
                id=dataset["name"],
                activity_id=activity.id,
            ),
            extra_environ=env,
            status=404,
        )

    def test_changes(self, app):
        user = factories.User()
        dataset = factories.Dataset(title="First title", user=user)
        dataset["title"] = "Second title"
        helpers.call_action("package_update", **dataset)

        activity = activity_model.package_activity_list(
            dataset["id"], limit=1, offset=0
        )[0]
        env = {"REMOTE_USER": user["name"]}
        response = app.get(
            url_for("activity.package_changes", id=activity.id),
            extra_environ=env,
        )
        assert helpers.body_contains(response, "First")
        assert helpers.body_contains(response, "Second")

    @pytest.mark.ckan_config("ckan.activity_list_limit", "3")
    def test_invalid_get_params(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url, query_string={"before": "XXX"}, status=400)
        assert "Invalid parameters" in response.body

    @pytest.mark.ckan_config("ckan.activity_list_limit", "3")
    def test_older_activities_url_button(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset["title"] = "Second title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "Third title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "Fourth title"
        helpers.call_action("package_update", **dataset)

        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(url)
        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        # Last activity in the first page
        before_time = datetime.fromisoformat(activities[2]["timestamp"])

        # Next page button
        older_activities_url_url = "/dataset/activity/{}?before={}".format(
            dataset["id"], before_time.timestamp()
        )
        assert older_activities_url_url in response.body

        # Prev page button is not in the first page
        newer_activities_url_url = "/dataset/activity/{}?after=".format(dataset["id"])
        assert newer_activities_url_url not in response.body

    @pytest.mark.ckan_config("ckan.activity_list_limit", "3")
    def test_next_before_buttons(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset["title"] = "Second title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "Third title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "4th title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "5th title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "6th title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "7h title"
        helpers.call_action("package_update", **dataset)

        db_activities = activity_model.package_activity_list(
            dataset["id"], limit=10
        )
        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"]
        )
        # Last activity in the first page
        last_act_page_1_time = datetime.fromisoformat(
            activities[2]["timestamp"]
        )
        url = url_for("activity.package_activity", id=dataset["id"])
        response = app.get(
            url, query_string={"before": last_act_page_1_time.timestamp()}
        )

        # Next page button exists in page 2
        older_activities_url_url = "/dataset/activity/{}?before={}".format(
            dataset["id"], db_activities[5].timestamp.timestamp()
        )
        assert older_activities_url_url in response.body
        # Prev page button exists in page 2
        newer_activities_url_url = "/dataset/activity/{}?after={}".format(
            dataset["id"], db_activities[3].timestamp.timestamp()
        )
        assert newer_activities_url_url in response.body

    @pytest.mark.ckan_config("ckan.activity_list_limit", "3")
    def test_newer_activities_url_button(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset["title"] = "Second title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "Third title"
        helpers.call_action("package_update", **dataset)
        dataset["title"] = "Fourth title"
        helpers.call_action("package_update", **dataset)

        activities = helpers.call_action(
            "package_activity_list", id=dataset["id"], limit=10
        )
        before_time = datetime.fromisoformat(activities[2]["timestamp"])

        url = url_for("activity.package_activity", id=dataset["id"])
        # url for page 2
        response = app.get(
            url, query_string={"before": before_time.timestamp()}
        )

        # There's not a third page
        older_activities_url_url = "/dataset/activity/{}?before=".format(dataset["name"])
        assert older_activities_url_url not in response.body

        # previous page exists
        after_time = datetime.fromisoformat(activities[3]["timestamp"])
        newer_activities_url_url = "/dataset/activity/{}?after={}".format(
            dataset["id"], after_time.timestamp()
        )
        assert newer_activities_url_url in response.body


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestGroup:
    def test_simple(self, app):
        """Checking the template shows the activity stream."""
        user = factories.User()
        group = factories.Group(user=user)

        url = url_for("activity.group_activity", id=group["id"])
        response = app.get(url)
        assert user["fullname"] in response
        assert "created the group" in response

    def test_create_group(self, app):
        user = factories.User()
        group = factories.Group(user=user)

        url = url_for("activity.group_activity", id=group["id"])
        response = app.get(url)
        assert_user_link_in_response(user, response)
        assert "created the group" in response
        assert_group_link_in_response(group, response)

    def test_change_group(self, app):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        group["title"] = "Group with changed title"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )

        url = url_for("activity.group_activity", id=group["id"])
        response = app.get(url)
        assert_user_link_in_response(user, response)
        assert "updated the group" in response
        assert_group_link_in_response(group, response)

    def test_delete_group_using_group_delete(self, app):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        helpers.call_action(
            "group_delete", context={"user": user["name"]}, **group
        )

        url = url_for("activity.group_activity", id=group["id"])
        env = {"REMOTE_USER": user["name"]}
        app.get(url, extra_environ=env, status=404)
        # group_delete causes the Member to state=deleted and then the user
        # doesn't have permission to see their own deleted Group. Therefore you
        # can't render the activity stream of that group. You'd hope that
        # group_delete was the same as group_update state=deleted but they are
        # not...

    def test_delete_group_by_updating_state(self, app):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        group["state"] = "deleted"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )

        url = url_for("activity.group_activity", id=group["id"])
        env = {"REMOTE_USER": user["name"]}
        response = app.get(url, extra_environ=env)
        assert_user_link_in_response(user, response)
        assert "deleted the group" in response
        assert_group_link_in_response(group, response)

    def test_create_dataset(self, app):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)

        url = url_for("activity.group_activity", id=group["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "created the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_change_dataset(self, app):

        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)
        _clear_activities()
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.group_activity", id=group["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_delete_dataset(self, app):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{"id": group["id"]}], user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        url = url_for("activity.group_activity", id=group["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert_user_link_in_response(user, response)
        assert "deleted the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()
