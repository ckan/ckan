# encoding: utf-8

"""
Tests for the ckanext.example_ipermissionlabels extension
"""

import pytest

from ckan import model
from ckan.plugins.toolkit import get_action, NotAuthorized
from ckan.tests import factories
from ckan.tests.helpers import call_auth


@pytest.mark.ckan_config('ckan.plugins', "example_ipermissionlabels")
@pytest.mark.usefixtures('clean_db', 'clean_index', 'with_plugins', 'with_request_context')
class TestExampleIPermissionLabels(object):
    def test_normal_dataset_permissions_are_normal(self):
        user = factories.User()
        user2 = factories.User()
        user3 = factories.User()
        org = factories.Organization(user=user)
        org2 = factories.Organization(
            user=user2, users=[{"name": user3["id"], "capacity": "member"}]
        )

        dataset = factories.Dataset(
            name="d1", user=user, private=True, owner_org=org["id"]
        )
        dataset2 = factories.Dataset(
            name="d2", user=user2, private=True, owner_org=org2["id"]
        )

        results = get_action("package_search")(
            {"user": user["name"]}, {"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == ["d1"]

        results = get_action("package_search")(
            {"user": user3["name"]}, {"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == ["d2"]

    def test_proposed_overrides_public(self):
        user = factories.User()
        dataset = factories.Dataset(name="d1", notes="Proposed:", user=user)

        results = get_action("package_search")(
            {"user": ""}, {"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == []

        with pytest.raises(NotAuthorized):
            call_auth(
                "package_show", {"user": "", "model": model}, id="d1"
            )

    def test_proposed_dataset_visible_to_creator(self):
        user = factories.User()
        dataset = factories.Dataset(name="d1", notes="Proposed:", user=user)

        results = get_action("package_search")(
            {"user": user["name"]}, {"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == ["d1"]

        ret = call_auth(
            "package_show", {"user": user["name"], "model": model}, id="d1"
        )
        assert ret

    def test_proposed_dataset_visible_to_org_admin(self):
        user = factories.User()
        user2 = factories.User()
        org = factories.Organization(
            user=user2, users=[{"name": user["id"], "capacity": "editor"}]
        )
        dataset = factories.Dataset(
            name="d1", notes="Proposed:", user=user, owner_org=org["id"]
        )

        results = get_action("package_search")(
            {"user": user2["name"]}, {"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == ["d1"]

        ret = call_auth(
            "package_show",
            {"user": user2["name"], "model": model},
            id="d1",
        )
        assert ret

    def test_proposed_dataset_invisible_to_another_editor(self):
        user = factories.User()
        user2 = factories.User()
        org = factories.Organization(
            user=user2, users=[{"name": user["id"], "capacity": "editor"}]
        )
        dataset = factories.Dataset(
            name="d1", notes="Proposed:", user=user2, owner_org=org["id"]
        )

        results = get_action("package_search")(
            {"user": user["name"]}, {"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == []

        with pytest.raises(NotAuthorized):
            call_auth(
                "package_show",
                {"user": user["name"], "model": model},
                id="d1",
            )
