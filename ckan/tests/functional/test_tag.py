from ckan.tests import *

class TestPackageController(TestControllerTwill):

    def _go_index(self):
        offset = url_for(controller='tag')
        url = self.siteurl + offset
        web.go(url)

    def test_index(self):
        self._go_index()
        web.code(200)
        web.title('Tags - Index')

