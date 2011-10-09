# These only test that the controller is passing on queries correctly
# to the search library. The search library is tested in:
# ckan/tests/lib/test_solr_package_search.py

import re
from nose.tools import assert_equal

from ckan.tests import (TestController, CreateTestData,
                        setup_test_search_index, html_check)
from ckan import model
import ckan.lib.search as search

class TestSearch(TestController, html_check.HtmlCheckMethods):
    # 'penguin' is in all test search packages
    q_all = u'penguin'

    @classmethod
    def setup_class(cls):
        model.Session.remove()
        setup_test_search_index()
        CreateTestData.create_search_test_data()
        cls.count_re = re.compile('<strong>(\d)</strong> datasets found')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.clear()

    def _pkg_names(self, result):
        return ' '.join(result['results'])

    def _check_results(self, res, expected_count, expected_package_names=[]):
        '''Takes a search result web page and determines whether the
        search results displayed match the expected count and names
        of packages.'''
        # get count
        content = self.named_div('content', res)
        count_match = self.count_re.search(content)
        assert count_match
        assert_equal(len(count_match.groups()), 1)
        count = int(count_match.groups()[0])
        assert_equal(count, expected_count)

        # check package names
        if isinstance(expected_package_names, basestring):
            expected_package_names = [expected_package_names]
        for expected_name in expected_package_names:
            expected_html = '<a href="/dataset/%s">' % expected_name
            assert expected_html in res.body, \
                   'Could not find package name %r in the results page'

    def test_1_all_records(self):
        res = self.app.get('/dataset?q')
        result = self._check_results(res, 6, 'gils')

    def test_1_name(self):
        # exact name
        res = self.app.get('/dataset?q=gils')
        result = self._check_results(res, 1, 'gils')

    def test_2_title(self):
        # exact title, one word
        res = self.app.get('/dataset?q=Opengov.se')
        result = self._check_results(res, 1, 'se-opengov')

        # multiple words
        res = self.app.get('/dataset?q=Government%20Expenditure')
        result = self._check_results(res, 1, 'uk-government-expenditure')
