from ckan.tests import *

class TestPackageController(TestControllerTwill):
    def test_index(self):
        offset = url_for(controller='tag')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        # web.title('Tags - Index')
