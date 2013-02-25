import datetime
from nose.tools import assert_equal

from ckan.lib.create_test_data import CreateTestData
from ckan import model

from ckanext.stats.stats import Stats, RevisionStats
from ckanext.stats.tests import StatsFixture

class TestStatsPlugin(StatsFixture):
    @classmethod
    def setup_class(cls):
        super(TestStatsPlugin, cls).setup_class()

        CreateTestData.create_arbitrary([
            {'name':'test1', 'groups':['grp1'], 'tags':['tag1']},
            {'name':'test2', 'groups':['grp1', 'grp2'], 'tags':['tag1']},
            {'name':'test3', 'groups':['grp1', 'grp2'], 'tags':['tag1', 'tag2']},
            {'name':'test4'},
            ],
            extra_user_names=['bob'],
            admins=['bob'],
            )
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
        CreateTestData.delete()
        
    def test_top_rated_packages(self):
        pkgs = Stats.top_rated_packages()
        assert pkgs == []

    def test_most_edited_packages(self):
        pkgs = Stats.most_edited_packages()
        pkgs = [(pkg.name, count) for pkg, count in pkgs]
        assert_equal(pkgs[0], ('test3', 3))
        assert_equal(pkgs[1][1], 2) 
        assert_equal(pkgs[2][1], 2) 
        assert_equal(pkgs[3], ('test1', 1)) 

    def test_largest_groups(self):
        grps = Stats.largest_groups()
        grps = [(grp.name, count) for grp, count in grps]
        assert_equal(grps, [('grp1', 3),
                            ('grp2', 2)])

    def test_top_tags(self):
        tags = Stats.top_tags()
        tags = [(tag.name, count) for tag, count in tags]
        assert_equal(tags, [('tag1', 3),
                            ('tag2', 1)])

    def test_top_package_owners(self):
        owners = Stats.top_package_owners()
        owners = [(owner.name, count) for owner, count in owners]
        assert_equal(owners, [('bob', 4)])

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
            return (date, [model.Session.query(model.Package).get(id).name for id in ids], num, cumulative)
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
