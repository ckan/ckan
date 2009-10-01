from ckan.tests import *

class TestAdminController(TestController):

    # TODO: reenable this test when we've worked out why it makes a few
    # subsequent tests fail (in test_group and test_package).
    def _test_index(self):
        response = self.app.get(url_for(controller='admin'))
        # Test response...
        assert '<h1>Models' in response, response
