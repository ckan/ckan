import webtest
from ckan.tests import TestController
from ckan.tests import is_search_supported

class TestCORS(TestController):

    def test_options(self):
        # need webtest as it has request method
        self.ourapp = webtest.TestApp(self.wsgiapp)
        out = self.ourapp.request('/', method='OPTIONS')
        assert out.status_int == 200, out
        print out
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
        assert headers['Access-Control-Allow-Methods'] == "POST, PUT, GET, DELETE"
        assert headers['Access-Control-Allow-Headers'] == "X-CKAN-API-KEY, Content-Type"

