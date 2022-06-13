# -*- coding: utf-8 -*-

import datetime
import pytest

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins", "reset_index")
class TestActivityPagination(object):

    def test_package_activity_pagination(self):
        """Test package activity list filters."""
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        begin = datetime.datetime.utcnow().timestamp()
        dataset["notes"] = "First Update"
        helpers.call_action(
            "package_update",
            context={"user": user["name"]},
            **dataset,
        )

        middle = datetime.datetime.utcnow().timestamp()
        dataset["notes"] = "Second Update"
        helpers.call_action(
            "package_update",
            context={"user": user["name"]},
            **dataset,
        )

        end = datetime.datetime.utcnow().timestamp()
        dataset["notes"] = "Third Update"
        helpers.call_action(
            "package_update",
            context={"user": user["name"]},
            **dataset,
        )

        assert begin < middle < end

        # Default call returns list ordered by time desc. (Most recent update first)
        complete_stream = helpers.call_action("package_activity_list",  context={}, id=dataset['id'])
        assert complete_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert complete_stream[-1]["data"]["package"]["notes"] == "First Update"

        # Offset call returns list ordered by time desc. (Most recent update first)
        offset_stream = helpers.call_action("package_activity_list",  context={}, id=dataset['id'], offset=0, limit=3)
        assert offset_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert offset_stream[-1]["data"]["package"]["notes"] == "First Update"

        # Before call
        before_stream = helpers.call_action("package_activity_list",  context={}, id=dataset['id'], before=middle)
        assert len(before_stream) == 1
        assert before_stream[0]["data"]["package"]["notes"] == "First Update"

        # After call
        after_stream = helpers.call_action("package_activity_list",  context={}, id=dataset['id'], after=middle)
        assert len(after_stream) == 2
        assert after_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert after_stream[1]["data"]["package"]["notes"] == "Second Update"

        # Before and After
        before_after_stream = helpers.call_action("package_activity_list",  context={}, id=dataset['id'], after=begin, before=end)
        assert len(before_after_stream) == 2
        assert before_after_stream[0]["data"]["package"]["notes"] == "Second Update"
        assert before_after_stream[1]["data"]["package"]["notes"] == "First Update"

        # Before now should retrieve all
        last_time = datetime.datetime.utcnow().timestamp()
        total_before_stream = helpers.call_action("package_activity_list",  context={}, id=dataset['id'], before=last_time)
        assert len(total_before_stream) == 3
        assert total_before_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert total_before_stream[1]["data"]["package"]["notes"] == "Second Update"
        assert total_before_stream[2]["data"]["package"]["notes"] == "First Update"

        # After middle with limit 1 should retrieve only the third update
        limit_after_stream = helpers.call_action("package_activity_list",  context={}, id=dataset['id'], after=middle, limit=1)
        assert len(limit_after_stream) == 1
        assert limit_after_stream[0]["data"]["package"]["notes"] == "Third Update"

        # After begin with limit 1 and offset 1 should retrieve only the second update
        after_offset_limit_stream = helpers.call_action("package_activity_list",  context={}, id=dataset['id'], after=middle, offset=1, limit=1)
        assert len(after_offset_limit_stream) == 1
        assert after_offset_limit_stream[0]["data"]["package"]["notes"] == "Second Update"

    def test_organization_activity_pagination(self):
        """Test organization activity list filters."""
        user = factories.Sysadmin()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        begin = datetime.datetime.utcnow().timestamp()
        dataset["notes"] = "First Update"
        helpers.call_action(
            "package_update",
            context={"user": user["name"]},
            **dataset,
        )

        middle = datetime.datetime.utcnow().timestamp()
        helpers.call_action(
            "organization_update",
            context={"user": user["name"]},
            id=org["id"],
            name="new-organization-name",
            title="New Organization Name",
        )

        end = datetime.datetime.utcnow().timestamp()
        dataset["notes"] = "Third Update"
        helpers.call_action(
            "package_update",
            context={"user": user["name"]},
            **dataset,
        )

        assert begin < middle < end

        # Default call returns list ordered by time desc. (Most recent update first)
        complete_stream = helpers.call_action("organization_activity_list",  context={}, id=org['id'])
        assert complete_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert complete_stream[-1]["data"]["package"]["notes"] == "First Update"

        # Offset call returns list ordered by time desc. (Most recent update first)
        offset_stream = helpers.call_action("organization_activity_list",  context={}, id=org['id'], offset=0, limit=3)
        assert offset_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert offset_stream[-1]["data"]["package"]["notes"] == "First Update"

        # Before call
        before_stream = helpers.call_action("organization_activity_list",  context={}, id=org['id'], before=middle)
        assert len(before_stream) == 1
        assert before_stream[0]["data"]["package"]["notes"] == "First Update"

        # After call
        after_stream = helpers.call_action("organization_activity_list",  context={}, id=org['id'], after=middle)
        assert len(after_stream) == 2
        assert after_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert after_stream[1]["data"]["group"]["title"] == "New Organization Name"
        assert after_stream[1]["activity_type"] == "changed organization"

        # Before and After
        before_after_stream = helpers.call_action("organization_activity_list",  context={}, id=org['id'], after=begin, before=end)
        assert len(before_after_stream) == 2
        assert before_after_stream[0]["activity_type"] == "changed organization"
        assert before_after_stream[1]["data"]["package"]["notes"] == "First Update"

        # Before now should retrieve all
        last_time = datetime.datetime.utcnow().timestamp()
        total_before_stream = helpers.call_action("organization_activity_list",  context={}, id=org['id'], before=last_time)
        assert len(total_before_stream) == 3
        assert total_before_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert total_before_stream[1]["activity_type"] == "changed organization"
        assert total_before_stream[2]["data"]["package"]["notes"] == "First Update"

        # After middle with limit 1 should retrieve only the third update
        limit_after_stream = helpers.call_action("organization_activity_list",  context={}, id=org['id'], after=middle, limit=1)
        assert len(limit_after_stream) == 1
        assert limit_after_stream[0]["data"]["package"]["notes"] == "Third Update"

        # After begin with limit 1 and offset 1 should retrieve only the second update
        after_offset_limit_stream = helpers.call_action("organization_activity_list",  context={}, id=org['id'], after=middle, offset=1, limit=1)
        assert len(after_offset_limit_stream) == 1
        assert after_offset_limit_stream[0]["activity_type"] == "changed organization"

    def test_group_activity_pagination(self):
        """Test group activity list filters."""
        user = factories.Sysadmin()
        group = factories.Group()
        dataset = factories.Dataset(groups=[{"id": group["id"]}])

        begin = datetime.datetime.utcnow().timestamp()
        dataset["notes"] = "First Update"
        helpers.call_action(
            "package_update",
            context={"user": user["name"]},
            **dataset,
        )

        middle = datetime.datetime.utcnow().timestamp()
        helpers.call_action(
            "group_update",
            context={"user": user["name"]},
            id=group["id"],
            name="new-group-name",
            title="New Group Name",
        )

        end = datetime.datetime.utcnow().timestamp()
        dataset["notes"] = "Third Update"
        helpers.call_action(
            "package_update",
            context={"user": user["name"]},
            **dataset,
        )

        assert begin < middle < end

        # Default call returns list ordered by time desc. (Most recent update first)
        complete_stream = helpers.call_action("group_activity_list",  context={}, id=group['id'])
        assert complete_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert complete_stream[-1]["data"]["package"]["notes"] == "First Update"

        # Offset call returns list ordered by time desc. (Most recent update first)
        offset_stream = helpers.call_action("group_activity_list",  context={}, id=group['id'], offset=0, limit=3)
        assert offset_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert offset_stream[-1]["data"]["package"]["notes"] == "First Update"

        # Before call
        before_stream = helpers.call_action("group_activity_list",  context={}, id=group['id'], before=middle)
        assert len(before_stream) == 1
        assert before_stream[0]["data"]["package"]["notes"] == "First Update"

        # After call
        after_stream = helpers.call_action("group_activity_list",  context={}, id=group['id'], after=middle)
        assert len(after_stream) == 2
        assert after_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert after_stream[1]["data"]["group"]["title"] == "New Group Name"
        assert after_stream[1]["activity_type"] == "changed group"

        # Before and After
        before_after_stream = helpers.call_action("group_activity_list",  context={}, id=group['id'], after=begin, before=end)
        assert len(before_after_stream) == 2
        assert before_after_stream[0]["activity_type"] == "changed group"
        assert before_after_stream[1]["data"]["package"]["notes"] == "First Update"

        # Before now should retrieve all
        last_time = datetime.datetime.utcnow().timestamp()
        total_before_stream = helpers.call_action("group_activity_list",  context={}, id=group['id'], before=last_time)
        assert len(total_before_stream) == 3
        assert total_before_stream[0]["data"]["package"]["notes"] == "Third Update"
        assert total_before_stream[1]["activity_type"] == "changed group"
        assert total_before_stream[2]["data"]["package"]["notes"] == "First Update"

        # After middle with limit 1 should retrieve only the third update
        limit_after_stream = helpers.call_action("group_activity_list",  context={}, id=group['id'], after=middle, limit=1)
        assert len(limit_after_stream) == 1
        assert limit_after_stream[0]["data"]["package"]["notes"] == "Third Update"

        # After begin with limit 1 and offset 1 should retrieve only the second update
        after_offset_limit_stream = helpers.call_action("group_activity_list",  context={}, id=group['id'], after=middle, offset=1, limit=1)
        assert len(after_offset_limit_stream) == 1
        assert after_offset_limit_stream[0]["activity_type"] == "changed group"
