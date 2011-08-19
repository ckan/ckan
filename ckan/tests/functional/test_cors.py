import webtest
from ckan.tests import TestController

class TestCORS(TestController):

    def test_options(self):
        # need webtest as it has request method
        self.ourapp = webtest.TestApp(self.wsgiapp)
        out = self.ourapp.request('/', method='OPTIONS')
        assert out.status_int == 200, out

    def test_headers(self):
        out = self.app.get('/')
        headers = dict(out.headers)
        print headers
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert headers['Access-Control-Allow-Methods'] == "POST, PUT, GET, OPTIONS"
        assert headers['Access-Control-Allow-Headers'] == "X-CKAN-API-KEY, Content-Type"

