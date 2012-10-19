from ckan.tests import TestController
from ckan.tests import is_search_supported

class TestCORS(TestController):

    def test_options(self):
        out = self.app._gen_request(method='OPTIONS', url='/', status=200)
        assert len(str(out.body)) == 0, 'OPTIONS must return no content'

    def test_headers(self):
        # the home page does a package search so have to skip this test if
        # search is not supported
        if not is_search_supported():
            from nose import SkipTest
            raise SkipTest("Search not supported")

        out = self.app.get('/')
        headers = dict(out.headers)
        print headers
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert headers['Access-Control-Allow-Methods'] == "POST, PUT, GET, DELETE, OPTIONS"
        assert headers['Access-Control-Allow-Headers'] == "X-CKAN-API-KEY, Authorization, Content-Type"

