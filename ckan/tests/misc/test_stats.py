import ckan.model as model
from ckan.tests import *
from ckan.lib.stats import Stats
from ckan.rating import set_rating

class TestStats(TestController):
    
    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()        
        CreateTestData.create_search_test_data()

##    @classmethod
##    def teardown_class(self):
##        model.repo.rebuild_db()

    def test_top_rated(self):
        # Rate some packages
        set_rating(u'ip1', model.Package.by_name(u'gils'), 2.5)
        set_rating(u'ip2', model.Package.by_name(u'gils'), 1.0)
        set_rating(u'ip3', model.Package.by_name(u'gils'), 1.0)
        set_rating(u'ip1', model.Package.by_name(u'us-gov-images'), 2.0)
        set_rating(u'ip1', model.Package.by_name(u'usa-courts-gov'), 5.0)

        res = Stats().top_rated_packages()
        assert len(res) == 3, res
        assert res[0] == (model.Package.by_name(u'usa-courts-gov'), 5.0), res[0]
        assert res[1] == (model.Package.by_name(u'us-gov-images'), 2.0), res[1]
        assert res[2] == (model.Package.by_name(u'gils'), 1.5), res[2]

    def test_most_edited(self):
        # Edit some packages
        def edit_pkg(name, number_of_edits):
            for i in range(number_of_edits):
                pkg = model.Package.by_name(unicode(name))
                model.repo.new_revision()
                pkg.title = pkg.title + u'_'
                model.repo.commit_and_remove()
        edit_pkg('gils', 5)
        edit_pkg('us-gov-images', 4)
        edit_pkg('usa-courts-gov', 1)
        model.Session.remove()

        res = Stats().most_edited_packages()
        assert len(res) > 5, res
        assert res[0] == (model.Package.by_name(u'gils'), 6), res[0]

    def test_largest_groups(self):
        # Add packages to groups
        model.Session.add(model.Group(u'tst1'))
        model.Session.add(model.Group(u'tst2'))
        model.Session.add(model.Group(u'tst3'))
        model.repo.commit_and_remove()

        model.repo.new_revision()
        for group in model.Session.query(model.Group):
            group.packages = []
        model.Group.by_name(u'tst1').packages = [model.Package.by_name(u'gils'),
                                                  model.Package.by_name(u'us-gov-images'),
                                                  model.Package.by_name(u'usa-courts-gov')]
        model.Group.by_name(u'tst2').packages = [model.Package.by_name(u'us-gov-images'),
                                                  model.Package.by_name(u'usa-courts-gov')]
        model.Group.by_name(u'tst3').packages = [model.Package.by_name(u'usa-courts-gov')]
        model.repo.commit_and_remove()

        res = Stats().largest_groups()
        assert len(res) > 2, res
        assert res[0] == (model.Group.by_name(u'tst1'), 3), res[0]
        assert res[1] == (model.Group.by_name(u'tst2'), 2), res[1]
        assert res[2] == (model.Group.by_name(u'tst3'), 1), res[2]
        
