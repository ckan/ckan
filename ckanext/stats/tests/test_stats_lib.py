# encoding: utf-8

import pytest
import copy

from ckan import model
from ckan.tests import factories


from ckanext.stats.stats import Stats
from ckanext.activity.tests.conftest import ActivityFactory


@pytest.mark.ckan_config('ckan.plugins', 'stats activity')
@pytest.mark.usefixtures("with_plugins", "with_request_context")
@pytest.mark.freeze_time
class TestStatsPlugin(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, with_request_context, freezer):
        # week 1
        freezer.move_to('2011-1-5')
        user = factories.User(name="bob")
        org_users = [{"name": user["name"], "capacity": "editor"}]
        org1 = factories.Organization(name="org1", users=org_users)
        group2 = factories.Group()
        tag1 = {"name": "tag1"}
        tag2 = {"name": "tag2"}
        dataset1 = factories.Dataset(
            name="test1", owner_org=org1["id"], tags=[tag1], user=user
        )
        dataset2 = factories.Dataset(
            name="test2",
            owner_org=org1["id"],
            groups=[{"name": group2["name"]}],
            tags=[tag1],
            user=user,
        )
        dataset3 = factories.Dataset(
            name="test3",
            owner_org=org1["id"],
            groups=[{"name": group2["name"]}],
            tags=[tag1, tag2],
            user=user,
            private=True,
        )
        dataset4 = factories.Dataset(name="test4", user=user)

        # week 2
        freezer.move_to('2011-1-12')
        model.Package.by_name(u'test2').delete()
        ActivityFactory(
            user_id=user["id"],
            object_id=dataset2["id"],
            activity_type="deleted package",
            data={"package": copy.deepcopy(
                dataset1), "actor": "Mr Someone"},
        )
        model.repo.commit_and_remove()

        # week 3
        freezer.move_to('2011-1-19')
        dataset3['title'] = "Test 3"
        model.repo.commit_and_remove()
        dataset1['title'] = 'Test 1'
        ActivityFactory(
            user_id=user["id"],
            object_id=dataset1["id"],
            activity_type="changed package",
            data={"package": copy.deepcopy(dataset1), "actor": "Mr Someone"},
        )
        freezer.move_to('2011-1-20')
        model.repo.commit_and_remove()
        dataset4['title'] = 'Test 4'
        ActivityFactory(
            user_id=user["id"],
            object_id=dataset4["id"],
            activity_type="changed package",
            data={"package": copy.deepcopy(dataset4), "actor": "Mr Someone"},
        )
        model.repo.commit_and_remove()

        # week 4
        freezer.move_to('2011-1-26')
        dataset3['notes'] = "Test 3 notes"
        model.repo.commit_and_remove()
        dataset4['notes'] = 'test4 dataset'
        ActivityFactory(
            user_id=user["id"],
            object_id=dataset4["id"],
            activity_type="changed package",
            data={"package": copy.deepcopy(dataset4), "actor": "Mr Someone"},
        )
        model.repo.commit_and_remove()

    def test_most_edited_packages(self):
        pkgs = Stats.most_edited_packages()
        pkgs = [(pkg.name, count) for pkg, count in pkgs]
        # test2 does not come up because it was deleted
        # test3 does not come up because it is private
        test1 = 'test1', 1
        test4 = 'test4', 2
        assert len(pkgs[0]) == len(test1)
        assert all([a == b for a, b in zip(pkgs[0], test4)])
        assert len(pkgs[1]) == len(test4)
        assert all([a == b for a, b in zip(pkgs[1], test1)])

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

    @pytest.mark.ckan_config("ckan.auth.public_user_details", True)
    def test_top_package_creators_public_user(self):
        creators = Stats.top_package_creators()
        creators = [(creator.name, count) for creator, count in creators]
        # Only 2 shown because one of them was deleted and the other one is
        # private
        assert creators == [("bob", 2)]

    @pytest.mark.ckan_config("ckan.auth.public_user_details", False)
    def test_top_package_creators_non_public_user(self):
        creators = Stats.top_package_creators()
        # The data is not available since ckan.auth.public_user_details is False
        assert creators == []

    def test_new_packages_by_week(self):
        new_packages_by_week = Stats.get_by_week('new_packages')
        # only 3 shown because one of them is private
        # private packages are not shown in activity table
        data1 = ('2011-01-03', set((u'test1', u'test2', u'test4')),
                 3, 3)
        data2 = ('2011-01-10', set([]), 0, 3)
        data3 = ('2011-01-17', set([]), 0, 3)
        data4 = ('2011-01-24', set([]), 0, 3)

        def get_results(week_number):
            date, ids, num, cumulative = new_packages_by_week[week_number]
            return (date, set([model.Session.query(model.Package).get(id).name
                               for id in ids]), num, cumulative)

        assert len(get_results(0)) == len(data1)
        assert all([a == b for a, b in zip(get_results(0), data1)])
        assert len(get_results(1)) == len(data2)
        assert all([a == b for a, b in zip(get_results(1), data2)])
        assert len(get_results(2)) == len(data3)
        assert all([a == b for a, b in zip(get_results(2), data3)])
        assert len(get_results(3)) == len(data4)
        assert all([a == b for a, b in zip(get_results(3), data4)])

    def test_deleted_packages_by_week(self):
        deleted_packages_by_week = Stats.get_by_week(
            'deleted_packages')
        data1 = ('2011-01-10', ['test2'], 1, 1)
        data2 = ('2011-01-17', [], 0, 1)
        data3 = ('2011-01-24', [], 0, 1)

        def get_results(week_number):
            date, ids, num, cumulative = deleted_packages_by_week[week_number]
            return (date, [model.Session.query(model.Package).get(id).name for
                           id in ids], num, cumulative)
        assert len(get_results(0)) == len(data1)
        assert all([a == b for a, b in zip(get_results(0), data1)])
        assert len(get_results(1)) == len(data2)
        assert all([a == b for a, b in zip(get_results(1), data2)])
        assert len(get_results(2)) == len(data3)
        assert all([a == b for a, b in zip(get_results(2), data3)])

    def test_revisions_by_week(self):
        revisions_by_week = Stats.get_by_week('package_revisions')

        def get_results(week_number):
            date, ids, num, cumulative = revisions_by_week[week_number]
            return (date, num, cumulative)
        num_setup_revs = revisions_by_week[0][2]
        data1 = ('2011-01-03', num_setup_revs, num_setup_revs)
        data2 = ('2011-01-10', 1, num_setup_revs + 1)
        data3 = ('2011-01-17', 2, num_setup_revs + 3)
        data4 = ('2011-01-24', 1, num_setup_revs + 4)
        assert 6 > num_setup_revs > 2, num_setup_revs
        assert len(get_results(0)) == len(data1)
        assert all([a == b for a, b in zip(get_results(0), data1)])
        assert len(get_results(1)) == len(data2)
        assert all([a == b for a, b in zip(get_results(1), data2)])
        assert len(get_results(2)) == len(data3)
        assert all([a == b for a, b in zip(get_results(2), data3)])
        assert len(get_results(3)) == len(data4)
        assert all([a == b for a, b in zip(get_results(3), data4)])

    def test_num_packages_by_week(self):
        num_packages_by_week = Stats.get_num_packages_by_week()
        # only 3 shown because one of them is private
        # private packages are not shown in activity table
        data1 = ('2011-01-03', 3, 3)
        data2 = ('2011-01-10', -1, 2)
        data3 = ('2011-01-17', 0, 2)
        data4 = ('2011-01-24', 0, 2)
        # e.g. [('2011-05-30', 3, 3)]
        assert len(num_packages_by_week[0]) == len(data1)
        assert all([a == b for a, b in zip(num_packages_by_week[0], data1)])
        assert len(num_packages_by_week[1]) == len(data2)
        assert all([a == b for a, b in zip(num_packages_by_week[1], data2)])
        assert len(num_packages_by_week[2]) == len(data3)
        assert all([a == b for a, b in zip(num_packages_by_week[2], data3)])
        assert len(num_packages_by_week[3]) == len(data4)
        assert all([a == b for a, b in zip(num_packages_by_week[3], data4)])
