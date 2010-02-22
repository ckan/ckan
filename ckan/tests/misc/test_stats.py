import datetime
import re

from pylons import config

import ckan.model as model
from ckan.tests import *
from ckan.lib.stats import Stats, RevisionStats
from ckan.lib import stats
from ckan.rating import set_rating
from ckan.model.authz import add_user_to_role


class TestStats(TestController):
    
    @classmethod
    def setup_class(self):
        CreateTestData.create_search_test_data()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_top_rated(self):
        # Rate some packages
        set_rating(u'ip1', model.Package.by_name(u'gils'), 2.5)
        set_rating(u'ip2', model.Package.by_name(u'gils'), 1.0)
        set_rating(u'ip3', model.Package.by_name(u'gils'), 1.0)
        set_rating(u'ip1', model.Package.by_name(u'us-gov-images'), 2.0)
        set_rating(u'ip1', model.Package.by_name(u'usa-courts-gov'), 5.0)

        res = Stats().top_rated_packages()
        assert len(res) == 3, res
        assert res[0] == (model.Package.by_name(u'usa-courts-gov'), 5.0, 1), res[0]
        assert res[1] == (model.Package.by_name(u'us-gov-images'), 2.0, 1), res[1]
        assert res[2] == (model.Package.by_name(u'gils'), 1.5, 3), res[2]

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
        
    def test_top_tags(self):
        res = Stats().top_tags()
        assert len(res) > 5, res
        assert res[0] == (model.Tag.by_name(u'gov'), 4), res[0]

        res = Stats().top_tags(returned_tag_info='id')
        gov = model.Tag.by_name(u'gov')
        assert res[0] == (gov.id, 4), res[0]

        res = Stats().top_tags(returned_tag_info='name')
        gov = model.Tag.by_name(u'gov')
        assert res[0] == (gov.name, 4), res[0]

    def test_top_package_owners(self):
        cath = model.User(name=u'Cath')
        bob = model.User(name=u'Bob')
        jill = model.User(name=u'Jill')
        nate = model.User(name=u'Nate')
        model.Session.add_all((cath, bob, jill, nate))
        model.repo.commit_and_remove()

        cath = model.User.by_name(u'Cath')
        bob = model.User.by_name(u'Bob')
        jill = model.User.by_name(u'Jill')
        nate = model.User.by_name(u'Nate')

        # add some package admins
        for pkg_name, user_names in {u'gils': (u'Cath', u'Bob', u'Jill'),
                                     u'us-gov-images': (u'Bob', u'Jill'),
                                     u'usa-courts-gov': [u'Jill']}.items():
            for user_name in user_names:
                user = model.User.by_name(user_name)
                package = model.Package.by_name(pkg_name)
                assert user, user_name
                assert package, pkg_name
                add_user_to_role(user, model.authz.Role.ADMIN, package)

        # add some decoy packages with editors
        user = model.User.by_name(u'Nate')
        for pkg_name in (u'usa-courts-gov', u'se-opengov'):
            package = model.Package.by_name(pkg_name)
            assert package
            add_user_to_role(user, model.authz.Role.EDITOR, package)

        # add some decoy groups with admins
        user = model.User.by_name(u'Nate')
        for group_name in (u'penguin', u'ukgov'):
            group = model.Group.by_name(group_name)
            assert group, group_name
            add_user_to_role(user, model.authz.Role.ADMIN, group)
        
        res = Stats().top_package_owners()
        print res
        assert len(res) == 3, res
        assert res[0] == (model.User.by_name(u'Jill'), 3), res[0]
        assert res[1] == (model.User.by_name(u'Bob'), 2), res[1]
        assert res[2] == (model.User.by_name(u'Cath'), 1), res[2]

class TimedRevision(TestController):
    # all these are date as stated plus a few hours
    datetime_this_week_started = datetime.datetime.now() - datetime.timedelta(\
        days=datetime.date.weekday(datetime.date.today()))
    datetime_last_week_started = datetime_this_week_started - \
                             datetime.timedelta(days=7)
    datetime_two_weeks_ago_started = datetime_this_week_started - \
                                 datetime.timedelta(days=14)
    date_this_week_started = datetime.date.today() - datetime.timedelta(days=datetime.date.weekday(datetime.date.today()))
    date_last_week_started = datetime.date.today() - datetime.timedelta(days=datetime.date.weekday(datetime.date.today()) + 7)
    date_two_weeks_ago_started = datetime.date.today() - datetime.timedelta(days=datetime.date.weekday(datetime.date.today()) + 14)

    @classmethod
    def _create_old_objects(self, num_packages, date, object_class):
        class_name = re.search('\.(\w+)\'', str(object_class)).groups()[0]
        rev = model.repo.new_revision()
        rev.message = u'%s created' % class_name
        rev.timestamp = date
        names = []
        for i in range(num_packages):
            name = u'%s_%i_created_%s' % (class_name, i, date.strftime('%d-%m-%Y'))
            obj = object_class(name=name)
            model.Session.add(obj)
            names.append(name)
        model.repo.commit_and_remove()
        return names

    @classmethod
    def _edit_package(self, pkg_name, date):
        rev = model.repo.new_revision()
        rev.message = u'package edited %s' % date.strftime('%d-%m-%Y')
        rev.timestamp = date
        pkg = model.Package.by_name(pkg_name)
        assert pkg
        pkg_name = pkg.name + '_EDITED'
        pkg.name = pkg_name
        model.repo.commit_and_remove()
        return pkg_name

class TestRateStatsSimple(TimedRevision):
    @classmethod
    def setup_class(self):
        # created a package last week
        names = self._create_old_objects(1, self.datetime_last_week_started, model.Package)
        self.pkg_name = names[0]

        # edited it this week
        self.pkg_name = self._edit_package(self.pkg_name, self.datetime_this_week_started + datetime.timedelta(hours=1))

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_get_new_packages(self):
        new_pkgs = RevisionStats().get_new_packages()
        assert len(new_pkgs) == 1, new_pkgs
        pkg = model.Package.by_name(self.pkg_name)
        assert pkg, self.pkg_name
        date_ = self.date_last_week_started
        assert new_pkgs[0][0] == pkg.id, new_pkgs[0]
        assert datetime.date.fromordinal(new_pkgs[0][1]) == date_, new_pkgs[0]
        assert new_pkgs[0] == (pkg.id, date_.toordinal()), new_pkgs[0]
                               
    def test_get_new_packages_by_week(self):
        pkgs_by_week = RevisionStats().get_by_week('new_packages')
        assert len(pkgs_by_week) == 2, pkgs_by_week
        pkg = model.Package.by_name(self.pkg_name)
        assert pkgs_by_week[0] == (self.date_last_week_started.strftime('%Y-%m-%d'),
                                   [pkg.id],
                                   1, 1), pkgs_by_week[0]
        assert pkgs_by_week[1] == (self.date_this_week_started.strftime('%Y-%m-%d'),
                                   [], 0, 1), pkgs_by_week[1]

    def test_get_package_revisions_by_week(self):
        package_revisions_by_week = RevisionStats().get_by_week('package_revisions')
        assert len(package_revisions_by_week) == 2, package_revisions_by_week
        assert model.Session.query(model.PackageRevision).count() == 2, model.Session.query(model.PackageRevision).all()
        change_rev, create_rev = model.Session.query(model.PackageRevision).all()
        assert package_revisions_by_week[0] == (self.date_last_week_started.strftime('%Y-%m-%d'),
                                   [create_rev.id],
                                   1, 1), package_revisions_by_week[0]
        assert package_revisions_by_week[1] == (self.date_this_week_started.strftime('%Y-%m-%d'),
                                   [change_rev.id], 1, 2), package_revisions_by_week[1]

    def test_package_addition_rate(self):
        res = RevisionStats().package_addition_rate(weeks_ago=1)
        assert res == 1, res
        res = RevisionStats().package_addition_rate(weeks_ago=0)
        assert res == 0, res

    def test_package_revision_rate(self):
        res = RevisionStats().package_revision_rate(weeks_ago=0)
        assert res == 1, res
        res = RevisionStats().package_revision_rate(weeks_ago=1)
        assert res == 1, res


class TestRateStats(TimedRevision):
    @classmethod
    def setup_class(self):
        # create some packages for last week
        self._create_old_objects(5, self.datetime_last_week_started, model.Package)
        self._create_old_objects(2, self.datetime_two_weeks_ago_started + datetime.timedelta(days=0), model.Package)
        self._create_old_objects(4, self.datetime_two_weeks_ago_started + datetime.timedelta(days=1), model.Package)
        names = self._create_old_objects(6, self.datetime_two_weeks_ago_started + datetime.timedelta(days=2), model.Package)

        # edits - shouldn't affect addition totals
        self._edit_package(names[0], self.datetime_two_weeks_ago_started + datetime.timedelta(days=2, hours=1))
        self._edit_package(names[1], self.datetime_last_week_started + datetime.timedelta(days=2, hours=1))
        self._edit_package(names[2], self.datetime_this_week_started + datetime.timedelta(hours=1))

        # decoy objects - shouldn't affect any package totals
        self._create_old_objects(1, self.datetime_last_week_started, model.Group)
        self._create_old_objects(1, self.datetime_two_weeks_ago_started, model.Group)

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_get_new_packages_by_week(self):
        pkgs_by_week = RevisionStats().get_by_week('new_packages')
        assert len(pkgs_by_week) == 3, pkgs_by_week
        assert pkgs_by_week[0][0] == self.date_two_weeks_ago_started.strftime('%Y-%m-%d'), pkgs_by_week[0]
        assert len(pkgs_by_week[0][1]) == 12, pkgs_by_week[0]
        assert pkgs_by_week[0][2:4] == (12, 12), pkgs_by_week[0][2:4]
        assert pkgs_by_week[1][0] == self.date_last_week_started.strftime('%Y-%m-%d'), pkgs_by_week[1]
        assert len(pkgs_by_week[1][1]) == 5, pkgs_by_week[1]
        assert pkgs_by_week[1][2:4] == (5, 17), pkgs_by_week[1]
        assert pkgs_by_week[2][0] == self.date_this_week_started.strftime('%Y-%m-%d'), pkgs_by_week[1]
        assert len(pkgs_by_week[2][1]) == 0, pkgs_by_week[2]
        assert pkgs_by_week[2][2:4] == (0, 17), pkgs_by_week[2]

    def test_get_package_revisions_by_week(self):
        revs_by_week = RevisionStats().get_by_week('package_revisions')
        assert len(revs_by_week) == 3, revs_by_week
        assert revs_by_week[0][0] == self.date_two_weeks_ago_started.strftime('%Y-%m-%d'), revs_by_week[0]
        assert len(revs_by_week[0][1]) == 13, revs_by_week[0]
        assert revs_by_week[0][2:4] == (13, 13), revs_by_week[0][2:4]
        assert revs_by_week[1][0] == self.date_last_week_started.strftime('%Y-%m-%d'), revs_by_week[1]
        assert len(revs_by_week[1][1]) == 6, revs_by_week[1]
        assert revs_by_week[1][2:4] == (6, 19), revs_by_week[1]
        assert revs_by_week[2][0] == self.date_this_week_started.strftime('%Y-%m-%d'), revs_by_week[1]
        assert len(revs_by_week[2][1]) == 1, revs_by_week[2]
        assert revs_by_week[2][2:4] == (1, 20), revs_by_week[2]

    def test_package_addition_rate(self):
        res = RevisionStats().package_addition_rate(weeks_ago=0)
        assert res == 0, res
        res = RevisionStats().package_addition_rate(weeks_ago=1)
        assert res == 5, res
        res = RevisionStats().package_addition_rate(weeks_ago=2)
        assert res == 12, res

    def test_package_revision_rate(self):
        res = RevisionStats().package_revision_rate(weeks_ago=1)
        assert res == 6, res
        res = RevisionStats().package_revision_rate(weeks_ago=2)
        assert res == 13, res
        res = RevisionStats().package_revision_rate(weeks_ago=0)
        assert res == 1, res

    
