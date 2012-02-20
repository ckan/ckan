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

    # TODO: do we test authz. In essence authz is same as for resource read /
    # edit which in turn is same as dataset read / edit and which is tested
    # extensively elsewhere ...
    def test_read(self):
        dataset = model.Package.by_name(CreateTestData.pkg_names[0])
        resource_id = dataset.resources[0].id
        offset = url_for('webstore_read', id=resource_id)
        res = self.app.get(offset)
        assert_equal(res.status, 200)
        assert_equal(res.body, '')
        headers = dict(res.headers)
        assert_equal(headers['X-Accel-Redirect'], '/elastic/ckan-test.ckan.net/%s?'
                % resource_id)

    def test_update(self):
        dataset = model.Package.by_name(CreateTestData.pkg_names[0])
        resource_id = dataset.resources[0].id

        offset = url_for('webstore_write', id='does-not-exist')
        res = self.app.post(offset, status=404)
        assert res.status == 404

        offset = url_for('webstore_write', id=resource_id)
        res = self.app.post(offset)
        # in fact visitor can edit!
        # assert res.status in [401,302], res.status
        assert res.status == 200

import json
import paste.fixture
import paste.proxy

app = paste.proxy.Proxy('http://localhost:8088')
testapp = paste.fixture.TestApp(app)

class TestItForReal:
    '''This is a test using the real setup with elasticsearch.
    
    It requires you to run nginx with config as per
    https://github.com/okfn/elastic-proxy/blob/master/elasticproxy plus,
    obviously, elasticsearch on port 9200.
    '''
    def test_01(self):
        offset = '/api/resource/a687ea97-c4d6-4386-b5ac-365744c59662/data'
        res = testapp.get(offset, status=400)
        assert res.status == 400
        data = {
            "user": "hamlet",
            "post_date": "2009-11-15T13:12:00",
            "message": "Trying out elasticsearch, so far so good?"
            }
        data = json.dumps(data)
        testapp.put(offset + '/1', data)
        out = testapp.get(offset + '/1')
        outdata = json.loads(out.body)
        assert outdata['_source']['user'] == 'hamlet', outdata

