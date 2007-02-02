from ckan.tests import *

class TestPackageController(TestControllerTwill):

    def test_index(self):
        offset = url_for(controller='package')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - Index')

    def test_list(self):
        offset = url_for(controller='package', action='list')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - List')
        web.find('annakarenina')
