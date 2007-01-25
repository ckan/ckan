from ckan.tests import *

class TestHomeController(TestController):
    def test_index(self):
        response = self.app.get(url_for(controller='home'))
        # Test response...