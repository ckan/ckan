from nose.tools import assert_raises

from ckan.tests import *
import ckan.model as model

from wsgi_ckanclient import *
from ckanclient import CkanApiError

class TestWsgiCkanClient(TestController):
    def setup(self):
        self.client = WsgiCkanClient(self.app)
        model.repo.rebuild_db() # Needed for full run of tests - not sure
                                # why annafan, tester and testpackage still
                                # exist.
        CreateTestData.create()
        
    def teardown(self):
        model.repo.rebuild_db()

    def test_get_package_registry(self):
        register = self.client.package_register_get()
        assert self.client.last_status == 200
        assert len(register) == 2, register

    def test_404(self):
        assert_raises(CkanApiError, self.client.open_url, '/random')
        assert self.client.last_status == 404
