from ckan.tests import *

class TestHomeController(TestControllerTwill):

    def test_home_page(self):
        offset = url_for(controller='home')
        url = self.siteurl
        web.go(url)
        web.code(200)
        web.find('Packages')

    def test_packages_link(self):
        offset = url_for(controller='home')
        url = self.siteurl
        web.go(url)
        web.code(200)
        web.follow('Packages')
        web.code(200)
        
    def test_tags_link(self):
        offset = url_for(controller='home')
        url = self.siteurl
        web.go(url)
        web.code(200)
        web.follow('Tags')
        web.code(200)
        
    def test_404(self):
        url = self.siteurl + '/some_nonexistent_url'
        web.go(url)
        web.code(404)

    def test_license(self):
        offset = url_for(controller='license')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.find('All</strong> material contained in CKAN is .*open')

