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

    dataset["notes"] = "First Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    dataset["notes"] = "Second Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    dataset["notes"] = "Third Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    dataset["notes"] = "Fourth Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    dataset["notes"] = "Fifth Update"
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
        dataset, _ = activities
        complete_stream = helpers.call_action(
            "package_activity_list", context={}, id=dataset["id"]
        )
        assert complete_stream[0]["data"]["package"]["notes"] == "Fifth Update"
        assert (
            complete_stream[-1]["data"]["package"]["notes"] == "First Update"
        )

    def test_offset_call_returns_ordered_by_time_desc(self, activities):
        dataset, _ = activities
        offset_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            offset=0,
            limit=3,
        )
        assert offset_stream[0]["data"]["package"]["notes"] == "Fifth Update"
        assert offset_stream[-1]["data"]["package"]["notes"] == "Third Update"

    def test_before_call_returns_ordered_by_time_desc(self, activities):
        dataset, times = activities
        before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=times[0],
        )
        assert len(before_stream) == 4
        assert before_stream[0]["data"]["package"]["notes"] == "Fourth Update"
        assert before_stream[-1]["data"]["package"]["notes"] == "First Update"

    def test_before_fifth_with_limit_2_should_get_fourth_and_third(self, activities):
        dataset, times = activities
        before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=times[0],
            limit=2,
        )
        assert len(before_stream) == 2
        assert before_stream[0]["data"]["package"]["notes"] == "Fourth Update"
        assert before_stream[-1]["data"]["package"]["notes"] == "Third Update"

    def test_after_call_returns_ordered_by_time_desc(self, activities):
        dataset, times = activities
        after_stream = helpers.call_action(
            "package_activity_list", context={}, id=dataset["id"], after=times[3]
        )
        assert len(after_stream) == 3
        assert after_stream[0]["data"]["package"]["notes"] == "Fifth Update"
        assert after_stream[1]["data"]["package"]["notes"] == "Fourth Update"
        assert after_stream[2]["data"]["package"]["notes"] == "Third Update"

    def test_before_and_after_calls_returs_ordered_by_time_desc(self, activities):
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
            == "Fourth Update"
        )
        assert (
            before_after_stream[-1]["data"]["package"]["notes"]
            == "Second Update"
        )

    def test_before_now_should_return_all(self, activities):
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
            == "Fifth Update"
        )
        assert (
            total_before_stream[-1]["data"]["package"]["notes"]
            == "First Update"
        )

    def test_after_returns_closer_elements_order_time_desc(self, activities):
        """
        Given [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        Whith after 6 and limit 2
        Returns [8, 7]
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
            == "Third Update"
        )
        assert (
            total_before_stream[-1]["data"]["package"]["notes"]
            == "Second Update"
        )
