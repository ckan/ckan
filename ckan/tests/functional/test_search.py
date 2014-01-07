# These only test that the controller is passing on queries correctly
# to the search library. The search library is tested in:
# ckan/tests/lib/test_solr_package_search.py

import re
from nose.tools import assert_equal

from ckan.tests import CreateTestData, setup_test_search_index, search_related
from ckan.tests.pylons_controller import PylonsTestCase
from base import FunctionalTestCase
from ckan import model
import ckan.lib.search as search
import ckan.lib.helpers as h

class TestSearch(FunctionalTestCase):
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
        res = self.app.get('/dataset?q=Opengov')
        result = self._check_results(res, 1, 'se-opengov')

        # multiple words
        res = self.app.get('/dataset?q=Government%20Expenditure')
        result = self._check_results(res, 1, 'uk-government-expenditure')

class TestSearch2(FunctionalTestCase, PylonsTestCase):#, TestPackageForm):

    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        setup_test_search_index()
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.clear()

    @search_related
    def test_search(self):
        offset = h.url_for(controller='package', action='search')
        print offset
        res = self.app.get(offset)
        assert 'Search - ' in res
        self._check_search_results(res, 'annakarenina', ['<strong>1</strong>', 'A Novel By Tolstoy'] )
        self._check_search_results(res, 'warandpeace', ['<strong>1</strong>'])
        self._check_search_results(res, 'warandpeace', ['<strong>1</strong>'])
        self._check_search_results(res, 'annakarenina', ['<strong>1</strong>'])
        # check for something that also finds tags ...
        self._check_search_results(res, 'russian', ['<strong>2</strong>'])

    @search_related
    def test_search_foreign_chars(self):
        offset = h.url_for(controller='package', action='search')
        res = self.app.get(offset)
        assert 'Search - ' in res
        self._check_search_results(res, u'th\xfcmb', ['<strong>1</strong>'])
        self._check_search_results(res, 'thumb', ['<strong>1</strong>'])

    @search_related
    def test_search_escape_chars(self):
        payload = '?q=fjdkf%2B%C2%B4gfhgfkgf%7Bg%C2%B4pk&search=Search+Packages+%C2%BB'
        offset = h.url_for(controller='package', action='search') + payload
        results_page = self.app.get(offset)
        assert 'Search - ' in results_page, results_page
        results_page = self.main_div(results_page)
        # solr's edismax parser won't throw an error, so this should return 0 results
        assert '>0<' in results_page, results_page

    def _check_search_results(self, page, terms, requireds):
        form = page.forms['dataset-search']
        form['q'] = terms.encode('utf8') # paste doesn't handle this!
        results_page = form.submit()
        assert 'Search - ' in results_page, results_page
        results_page = self.main_div(results_page)
        for required in requireds:
            if required not in results_page:
                print results_page
                print 'Could not find %r' % required
                raise AssertionError

class TestNonActivePackages(FunctionalTestCase):
    @classmethod
    def setup_class(self):
        setup_test_search_index()
        CreateTestData.create()
        self.non_active_name = u'test_nonactive'
        pkg = model.Package(name=self.non_active_name)
        model.repo.new_revision()
        model.Session.add(pkg)
        model.repo.commit_and_remove()

        pkg = model.Session.query(model.Package).filter_by(name=self.non_active_name).one()
        admin = model.User.by_name(u'joeadmin')
        model.setup_default_user_roles(pkg, [admin])
        model.repo.commit_and_remove()

        model.repo.new_revision()        
        pkg = model.Session.query(model.Package).filter_by(name=self.non_active_name).one()
        pkg.delete() # becomes non active
        model.repo.commit_and_remove()
        

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
        search.clear()

    @search_related
    def test_search(self):
        offset = h.url_for(controller='package', action='search')
        res = self.app.get(offset)
        assert 'Search - ' in res
        form = res.forms['dataset-search']
        form['q'] =  'name:' + str(self.non_active_name)
        results_page = form.submit()
        assert 'Search - ' in results_page, results_page
        assert '<strong>0</strong> datasets found' in results_page, (self.non_active_name, results_page)
