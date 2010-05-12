from ckan.tests import *

class TestHomeController(TestController):

    def test_home_page(self):
        offset = url_for('home')
        res = self.app.get(offset)
        print str(res)
        assert 'Packages' in res

    def test_packages_link(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res.click('Packages', index=0)
        
    def test_tags_link(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res.click('Tags')
        
    def test_404(self):
        offset = '/some_nonexistent_url'
        res = self.app.get(offset, status=404)

    def test_license(self):
        offset = url_for('license')
        res = self.app.get(offset)
        print str(res)
        assert 'The code that runs CKAN is open-source' in res

    def test_guide(self):
        url = url_for('guide')
        assert url == 'http://wiki.okfn.org/ckan/doc/'

    def test_search_packages(self):
        offset = url_for('home')
        res = self.app.get(offset)
        form = res.forms[0]
        form['q'] =  'anna'
        results_page = form.submit()
        assert 'Search packages' in results_page, results_page
        assert '>0<' in results_page, results_page

    # DISABLED because this is not on home page anymore
    def _test_register_new_package(self):
        offset = url_for('home')
        res = self.app.get(offset)
        form = res.forms[1]
        form['title'] =  'test title'
        results_page = form.submit()
        assert 'Register a New Package' in results_page, results_page
        assert '<input id="Package--title" name="Package--title" size="40" type="text" value="test title">' in results_page, results_page
        
