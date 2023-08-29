# -*- coding: utf-8 -*-

import datetime

import pytest

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.fixture
def activities():
    user = factories.User()
    org = factories.Organization()
    dataset = factories.Dataset(owner_org=org["id"])

    dataset["notes"] = "Update 0"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    dataset["notes"] = "Update 1"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    dataset["notes"] = "Update 2"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    dataset["notes"] = "Update 3"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    dataset["notes"] = "Update 4"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    activity_list = helpers.call_action(
        "package_activity_list", context={}, id=dataset["id"]
    )
    from_iso = datetime.datetime.fromisoformat
    activity_times = [
        from_iso(a["timestamp"]).timestamp() for a in activity_list
    ]

    return dataset, activity_times


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins", "activities")
class TestActivityPagination(object):
    def test_default_returns_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With no filters
        Returns [4, 3, 2, 1, 0]
        """
        dataset, _ = activities
        activity_list = helpers.call_action(
            "package_activity_list", context={}, id=dataset["id"]
        )
        assert activity_list[0]["data"]["package"]["notes"] == "Update 4"
        assert activity_list[-1]["data"]["package"]["notes"] == "Update 0"

    def test_offset_call_returns_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With offset 0 and limit 3
        Returns [4, 3, 2]
        """
        dataset, _ = activities
        activity_list = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            offset=0,
            limit=3,
        )
        assert activity_list[0]["data"]["package"]["notes"] == "Update 4"
        assert activity_list[-1]["data"]["package"]["notes"] == "Update 2"

    def test_before_call_returns_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With before 4
        Returns [3, 2, 1, 0]
        """
        dataset, times = activities
        activity_list = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=times[0],
        )
        assert len(activity_list) == 4
        assert activity_list[0]["data"]["package"]["notes"] == "Update 3"
        assert activity_list[-1]["data"]["package"]["notes"] == "Update 0"

    def test_before_4_with_limit_2_should_get_3_and_2(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With before 4 and limit 2
        Returns [3, 2]
        """
        dataset, times = activities
        activity_list = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=times[0],
            limit=2,
        )
        assert len(activity_list) == 2
        assert activity_list[0]["data"]["package"]["notes"] == "Update 3"
        assert activity_list[-1]["data"]["package"]["notes"] == "Update 2"

    def test_after_call_returns_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With after 1
        Returns [4, 3, 2]
        """
        dataset, times = activities
        activity_list = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            after=times[3],
        )
        assert len(activity_list) == 3
        assert activity_list[0]["data"]["package"]["notes"] == "Update 4"
        assert activity_list[1]["data"]["package"]["notes"] == "Update 3"
        assert activity_list[2]["data"]["package"]["notes"] == "Update 2"

    def test_before_and_after_returns_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With after 0 and before 4
        Returns [3, 2, 1]
        """
        dataset, times = activities
        activity_list = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            after=times[4],
            before=times[0],
        )
        assert len(activity_list) == 3
        assert activity_list[0]["data"]["package"]["notes"] == "Update 3"
        assert activity_list[-1]["data"]["package"]["notes"] == "Update 1"

    def test_before_now_should_return_all(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With before now
        Returns [4, 3, 2, 1, 0]
        """
        dataset, _ = activities
        now = datetime.datetime.utcnow().timestamp()
        activity_list = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=now,
        )
        assert len(activity_list) == 5
        assert activity_list[0]["data"]["package"]["notes"] == "Update 4"
        assert activity_list[-1]["data"]["package"]["notes"] == "Update 0"

    def test_after_returns_closer_elements_order_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        Whith after 0 and limit 2
        Returns [2, 1]
        """
        dataset, time = activities
        activity_list = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            after=time[4],
            limit=2,
        )
        assert len(activity_list) == 2
        assert activity_list[0]["data"]["package"]["notes"] == "Update 2"
        assert activity_list[-1]["data"]["package"]["notes"] == "Update 1"
