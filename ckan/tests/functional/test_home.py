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
        model.repo.clean_db()

    def test_home_page(self):
        offset = url_for('home')
        res = self.app.get(offset)
        assert 'Packages' in res

    @search_related
    def test_packages_link(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res.click('Search', index=0)
        
    def test_tags_link(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res.click('Tags', index=0)
        
    def test_404(self):
        offset = '/some_nonexistent_url'
        res = self.app.get(offset, status=404)

    def test_license(self):
        offset = url_for('license')
        res = self.app.get(offset)
        assert 'The CKAN code that runs this site is open-source' in res

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
    
    def test_template_footer_end(self):
        offset = url_for('home')
        res = self.app.get(offset)
        assert '<strong>TEST TEMPLATE_FOOTER_END TEST</strong>'

    # DISABLED because this is not on home page anymore
    def _test_register_new_package(self):
        offset = url_for('home')
        res = self.app.get(offset)
        form = res.forms[1]
        form['title'] =  'test title'
        results_page = form.submit()
        assert 'Register a New Package' in results_page, results_page
        assert '<input id="Package--title" name="Package--title" size="40" type="text" value="test title">' in results_page, results_page
        
