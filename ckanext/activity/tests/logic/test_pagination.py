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
        from_iso(a['timestamp']).timestamp() for a in activity_list
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
        complete_stream = helpers.call_action(
            "package_activity_list", context={}, id=dataset["id"]
        )
        assert complete_stream[0]["data"]["package"]["notes"] == "Update 4"
        assert (
            complete_stream[-1]["data"]["package"]["notes"] == "Update 0"
        )

    def test_offset_call_returns_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With offset 0 and limit 3
        Returns [4, 3, 2]
        """
        dataset, _ = activities
        offset_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            offset=0,
            limit=3,
        )
        assert offset_stream[0]["data"]["package"]["notes"] == "Update 4"
        assert offset_stream[-1]["data"]["package"]["notes"] == "Update 2"

    def test_before_call_returns_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With before 4
        Returns [3, 2, 1, 0]
        """
        dataset, times = activities
        before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=times[0],
        )
        assert len(before_stream) == 4
        assert before_stream[0]["data"]["package"]["notes"] == "Update 3"
        assert before_stream[-1]["data"]["package"]["notes"] == "Update 0"

    def test_before_4_with_limit_2_should_get_3_and_2(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With limit 2
        Returns [3, 2]
        """
        dataset, times = activities
        before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=times[0],
            limit=2,
        )
        assert len(before_stream) == 2
        assert before_stream[0]["data"]["package"]["notes"] == "Update 3"
        assert before_stream[-1]["data"]["package"]["notes"] == "Update 2"

    def test_after_call_returns_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With after 1
        Returns [4, 3, 2]
        """
        dataset, times = activities
        after_stream = helpers.call_action(
            "package_activity_list", context={}, id=dataset["id"], after=times[3]
        )
        assert len(after_stream) == 3
        assert after_stream[0]["data"]["package"]["notes"] == "Update 4"
        assert after_stream[1]["data"]["package"]["notes"] == "Update 3"
        assert after_stream[2]["data"]["package"]["notes"] == "Update 2"

    def test_before_and_after_calls_returs_ordered_by_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With after 0 and before 4
        Returns [3, 2, 1]
        """
        dataset, times = activities
        before_after_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            after=times[4],
            before=times[0],
        )
        assert len(before_after_stream) == 3
        assert (
            before_after_stream[0]["data"]["package"]["notes"]
            == "Update 3"
        )
        assert (
            before_after_stream[-1]["data"]["package"]["notes"]
            == "Update 1"
        )

    def test_before_now_should_return_all(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        With before now
        Returns [4, 3, 2, 1, 0]
        """
        dataset, _ = activities
        now = datetime.datetime.utcnow().timestamp()
        total_before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=now,
        )
        assert len(total_before_stream) == 5
        assert (
            total_before_stream[0]["data"]["package"]["notes"]
            == "Update 4"
        )
        assert (
            total_before_stream[-1]["data"]["package"]["notes"]
            == "Update 0"
        )

    def test_after_returns_closer_elements_order_time_desc(self, activities):
        """
        Given [4, 3, 2, 1, 0]
        Whith after 0 and limit 2
        Returns [2, 1]
        """
        dataset, time = activities
        total_before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            after=time[4],
            limit=2
        )
        assert len(total_before_stream) == 2
        assert (
            total_before_stream[0]["data"]["package"]["notes"]
            == "Update 2"
        )
        assert (
            total_before_stream[-1]["data"]["package"]["notes"]
            == "Update 1"
        )
