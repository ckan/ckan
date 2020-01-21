# encoding: utf-8

"""
Tests for the ckanext.example_ipermissionlabels extension
"""

import pytest

from ckan import model
from ckan.plugins.toolkit import get_action, NotAuthorized
from ckan.tests import factories
from ckan.tests.helpers import call_auth


@pytest.mark.ckan_config(u'ckan.plugins', u"example_ipermissionlabels")
@pytest.mark.usefixtures(u'clean_db', u'clean_index', u'with_plugins', u'with_request_context')
class TestExampleIPermissionLabels(object):
    def test_normal_dataset_permissions_are_normal(self):
        user = factories.User()
        user2 = factories.User()
        user3 = factories.User()
        org = factories.Organization(user=user)
        org2 = factories.Organization(
            user=user2, users=[{u"name": user3["id"], u"capacity": u"member"}]
        )

        dataset = factories.Dataset(
            name=u"d1", user=user, private=True, owner_org=org["id"]
        )
        dataset2 = factories.Dataset(
            name=u"d2", user=user2, private=True, owner_org=org2["id"]
        )

        results = get_action(u"package_search")(
            {u"user": user["name"]}, {u"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == [u"d1"]

        results = get_action(u"package_search")(
            {u"user": user3["name"]}, {u"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == [u"d2"]

    def test_proposed_overrides_public(self):
        user = factories.User()
        dataset = factories.Dataset(name=u"d1", notes=u"Proposed:", user=user)

        results = get_action(u"package_search")(
            {u"user": u""}, {u"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == []

        with pytest.raises(NotAuthorized):
            call_auth(
                u"package_show", {u"user": u"", u"model": model}, id=u"d1"
            )

    def test_proposed_dataset_visible_to_creator(self):
        user = factories.User()
        dataset = factories.Dataset(name=u"d1", notes=u"Proposed:", user=user)

        results = get_action(u"package_search")(
            {u"user": user["name"]}, {u"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == [u"d1"]

        ret = call_auth(
            u"package_show", {u"user": user["name"], u"model": model}, id=u"d1"
        )
        assert ret

    def test_proposed_dataset_visible_to_org_admin(self):
        user = factories.User()
        user2 = factories.User()
        org = factories.Organization(
            user=user2, users=[{u"name": user["id"], u"capacity": u"editor"}]
        )
        dataset = factories.Dataset(
            name=u"d1", notes=u"Proposed:", user=user, owner_org=org["id"]
        )

        results = get_action(u"package_search")(
            {u"user": user2[u"name"]}, {u"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == [u"d1"]

        ret = call_auth(
            u"package_show",
            {u"user": user2["name"], u"model": model},
            id=u"d1",
        )
        assert ret

    def test_proposed_dataset_invisible_to_another_editor(self):
        user = factories.User()
        user2 = factories.User()
        org = factories.Organization(
            user=user2, users=[{u"name": user["id"], u"capacity": u"editor"}]
        )
        dataset = factories.Dataset(
            name=u"d1", notes=u"Proposed:", user=user2, owner_org=org["id"]
        )

        results = get_action(u"package_search")(
            {u"user": user["name"]}, {u"include_private": True}
        )["results"]
        names = [r["name"] for r in results]
        assert names == []

        with pytest.raises(NotAuthorized):
            call_auth(
                u"package_show",
                {u"user": user["name"], u"model": model},
                id=u"d1",
            )
