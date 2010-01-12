import re

import ckan.model as model
import ckan.rating
from ckan.tests import *

class TestUsage(TestController):

    @classmethod
    def teardown(self):
        self.clear_all_tst_ratings()

    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()
        CreateTestData.create()
        self.clear_all_tst_ratings()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def _get_current_rating(self, res):
        res_str = res.body.decode('utf8')
        if not hasattr(self, 'rating_re'):
            # Hunt for something like:   3.5 (4 ratings)
            self.rating_re = re.compile('(\d.\d) \(\d ratings?\)')
        match = self.rating_re.search(res_str)
        if not match:
            assert res_str.find(u'no ratings yet')
            return None
        else:
            return float(match.groups()[0])
        
    def test_0_read_package(self):
        offset = url_for(controller='package', action='read', id=u'warandpeace')
        res = self.app.get(offset)
        assert 'Rating' in res, res
        assert '<ul class="stars default0star">' in res, res
        assert self._get_current_rating(res) == None

    def test_1_give_all_ratings(self):
        pkg_name = u'annakarenina'

        offset = url_for(controller='package', action='read', id=pkg_name)
        res = self.app.get(offset)
        for rating in range(1, 6):
            self.clear_all_tst_ratings()
            pkg = model.Package.by_name(pkg_name)
            res = res.click(href='rating=%s' % rating)
            res = res.follow()
            ave_rating, num_ratings = ckan.rating.get_rating(pkg)
            assert ave_rating == float(rating), rating
            assert num_ratings == 1, num_ratings
            assert self._get_current_rating(res) == float(rating), rating

    def test_2_give_two_ratings(self):
        pkg_name = u'annakarenina'
        pkg = model.Package.by_name(pkg_name)
        offset = url_for(controller='package', action='read', id=pkg_name)
        res = self.app.get(offset)
        assert self._get_current_rating(res) == None

        res = res.click(href='rating=4')

        offset = url_for(controller='package', action='read', id=pkg_name)
        res = self.app.get(offset)
        assert self._get_current_rating(res) == 4.0, self._get_current_rating(res)
        pkg = model.Package.by_name(pkg_name)
        ave_rating, num_ratings = ckan.rating.get_rating(pkg)
        assert ave_rating == 4.0, ave_rating
        assert num_ratings == 1, num_ratings

        res = res.click(href='rating=2')

        offset = url_for(controller='package', action='read', id=pkg_name)
        res = self.app.get(offset)
        assert self._get_current_rating(res) == 2.0, self._get_current_rating(res)
        pkg = model.Package.by_name(pkg_name)
        ave_rating, num_ratings = ckan.rating.get_rating(pkg)
        assert ave_rating == 2.0, ave_rating
        assert num_ratings == 1, num_ratings
        
    def test_3_rating_out_of_range(self):
        pkg_name = u'annakarenina'
        pkg = model.Package.by_name(pkg_name)
        offset = url_for(controller='package', action='read', id=pkg_name)
        res = self.app.get(offset)
        assert self._get_current_rating(res) == None, self._get_current_rating(res)

        offset = url_for(controller='package', action='rate', id=pkg_name)
        offset += '?rating=6'
        res = self.app.get(offset, status=400)

        assert self._get_current_rating(res) == None, res
