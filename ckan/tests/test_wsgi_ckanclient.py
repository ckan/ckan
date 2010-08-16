from ckan.tests import *
from wsgi_ckanclient import *

class TestWsgiCkanClient(TestController):
    def setup(self):
        self.client = WsgiCkanClient(self.app)
        CreateTestData.create()
        
    def teardown(self):
        CreateTestData.delete()        

    def test_get_package_registry(self):
        register = self.client.package_register_get()
        assert self.client.last_status == 200
        assert len(register) == 2, register

    def test_404(self):
        self.client.open_url('/random')
        assert self.client.last_status == 404
