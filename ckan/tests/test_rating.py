import ckan.model as model
import ckan.rating
from ckan.tests import *

class Annafan:
    user = u'annafan'

class Visitor:
    user = u''
    author = u'123.1.1.123'

class TestBasic(TestController):

    @classmethod
    def teardown(self):
        self.clear_all_tst_ratings()

    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_user_gives_rating(self):
        pkg_name = u'annakarenina'
        pkg = model.Package.by_name(pkg_name)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == None, average
        assert count == 0, count

        ckan.rating.set_my_rating(Annafan(),
                           model.Package.by_name(pkg_name),
                           4)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == 4.0
        assert count == 1

        pkg = model.Package.by_name(pkg_name)
        assert len(pkg.ratings) == 1, pkg.ratings
        rating = pkg.ratings[0]
        assert rating.user.name==u'annafan', rating.user
        assert rating.package.name==pkg_name, rating.package
        assert rating.rating==4, rating.rating

    def test_visitor_gives_rating(self):
        pkg_name = u'warandpeace'
        pkg = model.Package.by_name(pkg_name)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == None, average
        assert count == 0, count

        ckan.rating.set_my_rating(Visitor(),
                           model.Package.by_name(pkg_name),
                           3)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == 3.0
        assert count == 1

        pkg = model.Package.by_name(pkg_name)
        assert len(pkg.ratings) == 1, pkg.ratings
        rating = pkg.ratings[0]
        assert rating.user_ip_address==u'123.1.1.123', rating.user_ip_address
        assert rating.package.name==pkg_name, rating.package
        assert rating.rating==3, rating.rating

    def test_set_my_ratings(self):
        pkg_name = u'annakarenina'
        pkg = model.Package.by_name(pkg_name)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == None, average
        assert count == 0, count

        ckan.rating.set_my_rating(Annafan(),
                           model.Package.by_name(pkg_name),
                           4)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == 4.0
        assert count == 1

        ckan.rating.set_my_rating(Annafan(),
                           model.Package.by_name(pkg_name),
                           2)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == 2.0
        assert count == 1

        ckan.rating.set_my_rating(Annafan(),
                           model.Package.by_name(pkg_name),
                           2)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == 2.0
        assert count == 1

        ckan.rating.set_my_rating(Visitor(),
                           model.Package.by_name(pkg_name),
                           5)

        average, count = ckan.rating.get_rating(model.Package.by_name(pkg_name))
        assert average == 3.5
        assert count == 2
        
        
