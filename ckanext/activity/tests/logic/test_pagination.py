# -*- coding: utf-8 -*-

import datetime

import pytest

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins", "reset_index")
class TestActivityPagination(object):
    def test_package_activity_pagination(self):
        """Test package activity list filters."""
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

        assert first < second < third < fourth < fifth

        # Default call returns list ordered by time desc. (Most recent update first)
        complete_stream = helpers.call_action(
            "package_activity_list", context={}, id=dataset["id"]
        )
        assert complete_stream[0]["data"]["package"]["notes"] == "Fifth Update"
        assert (
            complete_stream[-1]["data"]["package"]["notes"] == "First Update"
        )

        # Offset call returns list ordered by time desc. (Most recent update first)
        offset_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            offset=0,
            limit=3,
        )
        assert offset_stream[0]["data"]["package"]["notes"] == "Fifth Update"
        assert offset_stream[-1]["data"]["package"]["notes"] == "Third Update"

        # Before call
        before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=fourth,
        )
        assert len(before_stream) == 3
        assert before_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert before_stream[-1]["data"]["package"]["notes"] == "First Update"

        # Before Fifth with limit 2 should get fourth and third
        before_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            before=fifth,
            limit=2,
        )
        assert len(before_stream) == 2
        assert before_stream[0]["data"]["package"]["notes"] == "Fourth Update"
        assert before_stream[-1]["data"]["package"]["notes"] == "Third Update"

        # After call
        after_stream = helpers.call_action(
            "package_activity_list", context={}, id=dataset["id"], after=third
        )
        assert len(after_stream) == 3
        assert after_stream[0]["data"]["package"]["notes"] == "Fifth Update"
        assert after_stream[1]["data"]["package"]["notes"] == "Fourth Update"
        assert after_stream[2]["data"]["package"]["notes"] == "Third Update"
        # Before and After
        before_after_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            after=first,
            before=fifth,
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

        # Before now should retrieve all
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

        # After middle with limit 1 should retrieve only the third update
        limit_after_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            after=third,
            limit=1,
        )
        assert len(limit_after_stream) == 1
        assert (
            limit_after_stream[0]["data"]["package"]["notes"] == "Fifth Update"
        )

        # After begin with limit 1 and offset 1 should retrieve only the second update
        after_offset_limit_stream = helpers.call_action(
            "package_activity_list",
            context={},
            id=dataset["id"],
            after=first,
            offset=1,
            limit=1,
        )
        assert len(after_offset_limit_stream) == 1
        assert (
            after_offset_limit_stream[0]["data"]["package"]["notes"]
            == "Fourth Update"
        )
