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

    first = datetime.datetime.utcnow().timestamp()
    dataset["notes"] = "First Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    second = datetime.datetime.utcnow().timestamp()
    dataset["notes"] = "Second Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    third = datetime.datetime.utcnow().timestamp()
    dataset["notes"] = "Third Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    fourth = datetime.datetime.utcnow().timestamp()
    dataset["notes"] = "Fourth Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )

    fifth = datetime.datetime.utcnow().timestamp()
    dataset["notes"] = "Fifth Update"
    helpers.call_action(
        "package_update",
        context={"user": user["name"]},
        **dataset,
    )
    return dataset, [first, second, third, fourth, fifth]


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
            before=times[3],
        )
        assert len(before_stream) == 3
        assert before_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert before_stream[-1]["data"]["package"]["notes"] == "First Update"

    def test_before_fifth_with_limit_2_should_get_fourth_and_third(self, activities):
        dataset, times = activities
        before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=times[4],
            limit=2,
        )
        assert len(before_stream) == 2
        assert before_stream[0]["data"]["package"]["notes"] == "Fourth Update"
        assert before_stream[-1]["data"]["package"]["notes"] == "Third Update"

    def test_after_call_returns_ordered_by_time_desc(self, activities):
        dataset, times = activities
        after_stream = helpers.call_action(
            "package_activity_list", context={}, id=dataset["id"], after=times[2]
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
            after=times[0],
            before=times[4],
        )
        assert len(before_after_stream) == 4
        assert (
            before_after_stream[0]["data"]["package"]["notes"]
            == "Fourth Update"
        )
        assert (
            before_after_stream[-1]["data"]["package"]["notes"]
            == "First Update"
        )

    def test_before_now_should_return_all(self, activities):
        dataset, _ = activities
        last_time = datetime.datetime.utcnow().timestamp()
        total_before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=last_time,
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
