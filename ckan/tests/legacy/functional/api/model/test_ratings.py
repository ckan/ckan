# encoding: utf-8

from nose.tools import assert_equal
from nose.plugins.skip import SkipTest

from ckan import model
from ckan.lib.create_test_data import CreateTestData

from ckan.tests.legacy.functional.api.base import BaseModelApiTestCase


class RatingsTestCase(BaseModelApiTestCase):

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.testsysadmin = model.User.by_name(u'testsysadmin')
        cls.comment = u'Comment umlaut: \xfc.'
        cls.user_name = u'annafan' # created in CreateTestData
        cls.init_extra_environ(cls.user_name)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_register_get(self):
        raise SkipTest('"Rating register get" functionality is not implemented')
        rating1 = model.Rating(user_ip_address='1.2.3.4',
                               package=self.anna,
                               rating=4.0)
        rating2 = model.Rating(user=model.User.by_name(u'annafan'),
                               package=self.anna,
                               rating=2.0)
        model.Session.add_all((rating1, rating2))
        model.repo.commit_and_remove()

        offset = self.rating_offset()
        res = self.app.get(offset, status=[200])

    def test_entity_get(self):
        raise SkipTest('"Rating entity get" functionality is not implemented')
        rating = model.Rating(user_ip_address='1.2.3.4',
                              package=self.anna,
                              rating=4.0)
        model.Session.add(rating)
        model.repo.commit_and_remove()

        offset = self.rating_offset(self.anna.name)
        res = self.app.get(offset, status=[200])
        assert_equal(res, rating_opts['rating'])

    def test_register_post(self):
        # Test Rating Register Post 200.
        self.clear_all_tst_ratings()
        offset = self.rating_offset()
        rating_opts = {'package':u'warandpeace',
                       'rating':5}
        pkg_name = rating_opts['package']
        postparams = '%s=1' % self.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[201],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = self.get_package_by_name(pkg_name)
        assert pkg
        assert len(pkg.ratings) == 1
        assert pkg.ratings[0].rating == rating_opts['rating'], pkg.ratings

        # Get package to see rating
        offset = self.package_offset(pkg_name)
        res = self.app.get(offset, status=[200])
        assert pkg_name in res, res
        assert '"ratings_average": %s.0' % rating_opts['rating'] in res, res
        assert '"ratings_count": 1' in res, res

        model.Session.remove()

        # Rerate package
        offset = self.rating_offset()
        postparams = '%s=1' % self.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[201],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = self.get_package_by_name(pkg_name)
        assert pkg
        assert len(pkg.ratings) == 1
        assert pkg.ratings[0].rating == rating_opts['rating'], pkg.ratings

    def test_entity_post_invalid(self):
        self.clear_all_tst_ratings()
        offset = self.rating_offset()
        rating_opts = {'package':u'warandpeace',
                       'rating':0}
        postparams = '%s=1' % self.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[409],
                            extra_environ=self.extra_environ)
        self.assert_json_response(res, 'rating')
        model.Session.remove()
        pkg = self.get_package_by_name(rating_opts['package'])
        assert pkg
        assert len(pkg.ratings) == 0
