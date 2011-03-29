from ckan.tests import *
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model
from ckan.tests import search_related

class TestHomeController(TestController):
    @classmethod
    def setup_class(self):
        model.repo.init_db()
        CreateTestData.create()
        
    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    @search_related
    def test_home_page(self):
        offset = url_for('home')
        res = self.app.get(offset)
        assert 'Packages' in res

    @search_related
    def test_packages_link(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res.click('Search', index=0)
        
    @search_related
    def test_tags_link(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res.click('Tags', index=0)
        
    def test_404(self):
        offset = '/some_nonexistent_url'
        res = self.app.get(offset, status=404)

    def test_guide(self):
        url = url_for('guide')
        assert url == 'http://wiki.okfn.org/ckan/doc/'

    @search_related
    def test_search_packages(self):
        offset = url_for('home')
        res = self.app.get(offset)
        form = res.forms['package-search']
        form['q'] =  'anna'
        results_page = form.submit()
        assert 'Search - ' in results_page, results_page
        assert '>0<' in results_page, results_page
    
    @search_related
    def test_template_footer_end(self):
        offset = url_for('home')
        res = self.app.get(offset)
        assert '<strong>TEST TEMPLATE_FOOTER_END TEST</strong>'

    # DISABLED because this is not on home page anymore
    @search_related
    def _test_register_new_package(self):
        offset = url_for('home')
        res = self.app.get(offset)
        form = res.forms[1]
        form['title'] =  'test title'
        results_page = form.submit()
        assert 'Register a New Package' in results_page, results_page
        assert '<input id="Package--title" name="Package--title" size="40" type="text" value="test title">' in results_page, results_page
        
    @search_related
    def test_locale_change(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res = res.click('Deutsch')
        try:
            res = res.follow()
            assert 'Willkommen' in res.body
        finally:
            res = res.click('English')

    @search_related
    def test_locale_change_with_false_hash(self):
        offset = url_for('home')
        res = self.app.get(offset)
        found_html, found_desc, found_attrs = res._find_element(
            tag='a', href_attr='href',
            href_extract=None,
            content='Deutsch',
            id=None, 
            href_pattern=None,
            html_pattern=None,
            index=None, verbose=False)
        href = found_attrs['uri']
        assert href
        res = res.goto(href)
        try:
            assert res.status == 302, res.status # redirect

            href = href.replace('return_to=%2F&', 'return_to=%2Fhackedurl&')
            res = res.goto(href)
            assert res.status == 200, res.status # doesn't redirect
        finally:
            offset = url_for('home')
            res = self.app.get(offset)
            res = res.click('English')
