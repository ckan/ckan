from ckan.tests import *
from ckan.tests.pylons_controller import PylonsTestCase
import ckan.model as model

class TestWebstoreController(TestController, PylonsTestCase):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        model.repo.init_db()
        CreateTestData.create()
        
    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_01(self):
        resource_id = '123'
        offset = url_for('webstore', id=resource_id)
        print offset
        res = self.app.get(offset)

