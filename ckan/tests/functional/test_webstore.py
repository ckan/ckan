from nose.tools import assert_equal

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

    def test_read(self):
        dataset = model.Package.by_name(CreateTestData.pkg_names[0])
        resource_id = dataset.resources[0].id
        offset = url_for('webstore', id=resource_id)
        res = self.app.get(offset)
        assert_equal(res.status, 200)
        assert_equal(res.body, resource_id)

