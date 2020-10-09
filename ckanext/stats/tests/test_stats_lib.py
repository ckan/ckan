# encoding: utf-8

import datetime
import pytest

from ckan import model
from ckan.tests import factories

from ckanext.stats.stats import Stats


@pytest.mark.ckan_config('ckan.plugins', 'stats')
@pytest.mark.usefixtures("with_plugins", "with_request_context")
class TestStatsPlugin(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, with_request_context):
        user = factories.User(name="bob")
        org_users = [{"name": user["name"], "capacity": "editor"}]
        org1 = factories.Organization(name="org1", users=org_users)
        group2 = factories.Group()
        tag1 = {"name": "tag1"}
        tag2 = {"name": "tag2"}
        factories.Dataset(
            name="test1", owner_org=org1["id"], tags=[tag1], user=user
        )
        factories.Dataset(
            name="test2",
            owner_org=org1["id"],
            groups=[{"name": group2["name"]}],
            tags=[tag1],
            user=user,
        )
        factories.Dataset(
            name="test3",
            owner_org=org1["id"],
            groups=[{"name": group2["name"]}],
            tags=[tag1, tag2],
            user=user,
            private=True,
        )
        factories.Dataset(name="test4", user=user)

        # week 2
        model.Package.by_name(u"test2").delete()
        model.repo.commit_and_remove()

        # week 3
        model.Package.by_name(u"test3").title = "Test 3"
        model.repo.commit_and_remove()
        model.Package.by_name(u"test4").title = "Test 4"
        model.repo.commit_and_remove()

        # week 4
        model.Package.by_name(u"test3").notes = "Test 3 notes"
        model.repo.commit_and_remove()

    def test_top_rated_packages(self):
        pkgs = Stats.top_rated_packages()
        assert pkgs == []

    def test_largest_groups(self):
        grps = Stats.largest_groups()
        grps = [(grp.name, count) for grp, count in grps]
        # test2 does not come up because it was deleted
        # test3 does not come up because it is private
        assert grps == [
            ("org1", 1),
        ]

    def test_top_tags(self):
        tags = Stats.top_tags()
        tags = [(tag.name, count) for tag, count in tags]
        assert tags == [("tag1", 1)]

    def test_top_package_creators(self):
        creators = Stats.top_package_creators()
        creators = [(creator.name, count) for creator, count in creators]
        # Only 2 shown because one of them was deleted and the other one is
        # private
        assert creators == [("bob", 2)]
