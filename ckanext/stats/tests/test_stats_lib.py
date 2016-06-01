# encoding: utf-8

import datetime
from nose.tools import assert_equal

from ckan import model
from ckan.tests import factories

from ckanext.stats.stats import Stats, RevisionStats
from ckanext.stats.tests import StatsFixture


class TestStatsPlugin(StatsFixture):
    @classmethod
    def setup_class(cls):

        super(TestStatsPlugin, cls).setup_class()

        model.repo.rebuild_db()

        user = factories.User(name='bob')
        org_users = [{'name': user['name'], 'capacity': 'editor'}]
        org1 = factories.Organization(name='org1', users=org_users)
        group2 = factories.Group()
        tag1 = {'name': 'tag1'}
        tag2 = {'name': 'tag2'}
        factories.Dataset(name='test1', owner_org=org1['id'], tags=[tag1],
                          user=user)
        factories.Dataset(name='test2', owner_org=org1['id'], groups=[{'name':
                          group2['name']}], tags=[tag1], user=user)
        factories.Dataset(name='test3', owner_org=org1['id'], groups=[{'name':
                          group2['name']}], tags=[tag1, tag2], user=user,
                          private=True)
        factories.Dataset(name='test4', user=user)
        # hack revision timestamps to be this date
        week1 = datetime.datetime(2011, 1, 5)
        for rev in model.Session.query(model.Revision):
            rev.timestamp = week1 + datetime.timedelta(seconds=1)

        # week 2
        rev = model.repo.new_revision()
        rev.author = 'bob'
        rev.timestamp = datetime.datetime(2011, 1, 12)
        model.Package.by_name(u'test2').delete()
        model.repo.commit_and_remove()

        # week 3
        rev = model.repo.new_revision()
        rev.author = 'sandra'
        rev.timestamp = datetime.datetime(2011, 1, 19)
        model.Package.by_name(u'test3').title = 'Test 3'
        model.repo.commit_and_remove()
        rev = model.repo.new_revision()
        rev.author = 'sandra'
        rev.timestamp = datetime.datetime(2011, 1, 20)
        model.Package.by_name(u'test4').title = 'Test 4'
        model.repo.commit_and_remove()

        # week 4
        rev = model.repo.new_revision()
        rev.author = 'bob'
        rev.timestamp = datetime.datetime(2011, 1, 26)
        model.Package.by_name(u'test3').notes = 'Test 3 notes'
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(cls):

        model.repo.rebuild_db()

        model.Session.remove()

    def test_top_rated_packages(self):
        pkgs = Stats.top_rated_packages()
        assert pkgs == []

    def test_most_edited_packages(self):
        pkgs = Stats.most_edited_packages()
        pkgs = [(pkg.name, count) for pkg, count in pkgs]
        # test2 does not come up because it was deleted
        # test3 does not come up because it is private
        assert_equal(pkgs[0], ('test4', 2))
        assert_equal(pkgs[1], ('test1', 1))

    def test_largest_groups(self):
        grps = Stats.largest_groups()
        grps = [(grp.name, count) for grp, count in grps]
        # test2 does not come up because it was deleted
        # test3 does not come up because it is private
        assert_equal(grps, [('org1', 1), ])

    def test_top_tags(self):
        tags = Stats.top_tags()
        tags = [(tag.name, count) for tag, count in tags]
        assert_equal(tags, [('tag1', 1L)])

    def test_top_package_creators(self):
        creators = Stats.top_package_creators()
        creators = [(creator.name, count) for creator, count in creators]
        # Only 2 shown because one of them was deleted and the other one is
        # private
        assert_equal(creators, [('bob', 2)])

    def test_new_packages_by_week(self):
        new_packages_by_week = RevisionStats.get_by_week('new_packages')
        def get_results(week_number):
            date, ids, num, cumulative = new_packages_by_week[week_number]
            return (date, set([model.Session.query(model.Package).get(id).name for id in ids]), num, cumulative)
        assert_equal(get_results(0),
                     ('2011-01-03', set((u'test1', u'test2', u'test3', u'test4')), 4, 4))
        assert_equal(get_results(1),
                     ('2011-01-10', set([]), 0, 4))
        assert_equal(get_results(2),
                     ('2011-01-17', set([]), 0, 4))
        assert_equal(get_results(3),
                     ('2011-01-24', set([]), 0, 4))

    def test_deleted_packages_by_week(self):
        deleted_packages_by_week = RevisionStats.get_by_week('deleted_packages')
        def get_results(week_number):
            date, ids, num, cumulative = deleted_packages_by_week[week_number]
            return (date, [model.Session.query(model.Package).get(id).name for
                           id in ids], num, cumulative)
        assert_equal(get_results(0),
                     ('2011-01-10', [u'test2'], 1, 1))
        assert_equal(get_results(1),
                     ('2011-01-17', [], 0, 1))
        assert_equal(get_results(2),
                     ('2011-01-24', [], 0, 1))
        assert_equal(get_results(3),
                     ('2011-01-31', [], 0, 1))

    def test_revisions_by_week(self):
        revisions_by_week = RevisionStats.get_by_week('package_revisions')
        def get_results(week_number):
            date, ids, num, cumulative = revisions_by_week[week_number]
            return (date, num, cumulative)
        num_setup_revs = revisions_by_week[0][2]
        assert 6 > num_setup_revs > 2, num_setup_revs
        assert_equal(get_results(0),
                     ('2011-01-03', num_setup_revs, num_setup_revs))
        assert_equal(get_results(1),
                     ('2011-01-10', 1, num_setup_revs+1))
        assert_equal(get_results(2),
                     ('2011-01-17', 2, num_setup_revs+3))
        assert_equal(get_results(3),
                     ('2011-01-24', 1, num_setup_revs+4))

    def test_num_packages_by_week(self):
        num_packages_by_week = RevisionStats.get_num_packages_by_week()
        # e.g. [('2011-05-30', 3, 3)]
        assert_equal(num_packages_by_week[0], ('2011-01-03', 4, 4))
        assert_equal(num_packages_by_week[1], ('2011-01-10', -1, 3))
        assert_equal(num_packages_by_week[2], ('2011-01-17', 0, 3))
        assert_equal(num_packages_by_week[3], ('2011-01-24', 0, 3))
