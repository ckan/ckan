from ckan.tests import *

class TestHomeController(TestController2):

    def test_home_page(self):
        offset = url_for(controller='home')
        res = self.app.get(offset)
        print str(res)
        assert 'Packages' in res

    def test_packages_link(self):
        offset = url_for(controller='home')
        res = self.app.get(offset)
        res.click('Packages')
        
    def test_tags_link(self):
        offset = url_for(controller='home')
        res = self.app.get(offset)
        res.click('Tags')
        
    def test_404(self):
        offset = '/some_nonexistent_url'
        res = self.app.get(offset, status=404)

    def test_license(self):
        offset = url_for(controller='license')
        res = self.app.get(offset)
        print str(res)
        assert 'All content and data on CKAN is ' in res

