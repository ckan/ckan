import json
from nose.tools import assert_equal
from pylons import config

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
        offset = url_for('datastore_read', id=resource_id)
        res = self.app.get(offset)
        assert_equal(res.status, 200)
        data = json.loads(res.body)
        assert 'error' in data

        dataset.resources[0].webstore_url = 'enabled'
        model.repo.new_revision()
        model.Session.add(dataset.resources[0])
        model.Session.commit()

        offset = url_for('datastore_read', id=resource_id)
        res = self.app.get(offset)
        assert_equal(res.status, 200)
        assert_equal(res.body, '""')
        headers = dict(res.headers)
        assert_equal(headers['X-Accel-Redirect'], '/elastic/ckan-%s/%s?'
                % (config['ckan.site_id'], resource_id))

        offset = url_for('datastore_read', id=resource_id, url='/_search')
        res = self.app.get(offset)
        assert_equal(res.status, 200)
        headers = dict(res.headers)
        assert_equal(headers['X-Accel-Redirect'], '/elastic/ckan-%s/%s/_search?'
                % (config['ckan.site_id'], resource_id))

    def test_update(self):
        dataset = model.Package.by_name(CreateTestData.pkg_names[0])
        resource_id = dataset.resources[0].id

        offset = url_for('datastore_write', id='does-not-exist')
        res = self.app.post(offset, status=404)
        assert res.status == 404

        dataset.resources[0].webstore_url = ''
        model.repo.new_revision()
        model.Session.add(dataset.resources[0])
        model.Session.commit()

        offset = url_for('datastore_write', id=resource_id)
        res = self.app.post(offset)
        assert res.status == 200
        print res.body
        assert 'error' in json.loads(res.body)

        dataset.resources[0].webstore_url = 'enabled'
        model.repo.new_revision()
        model.Session.add(dataset.resources[0])
        model.Session.commit()

        offset = url_for('datastore_write', id=resource_id)
        res = self.app.post(offset)
        # in fact visitor can edit!
        # assert res.status in [401,302], res.status
        assert res.status == 200
        headers = dict(res.headers)
        assert_equal(headers['X-Accel-Redirect'], '/elastic/ckan-%s/%s?'
                % (config['ckan.site_id'], resource_id))


        offset = url_for('datastore_write', id=resource_id, url='/_mapping')
        res = self.app.post(offset)
        assert res.status == 200
        headers = dict(res.headers)
        assert_equal(headers['X-Accel-Redirect'], '/elastic/ckan-%s/%s/_mapping?'
                % (config['ckan.site_id'], resource_id))

