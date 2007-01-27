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
        
