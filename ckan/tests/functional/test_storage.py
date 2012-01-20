import os
from paste.deploy import appconfig
import paste.fixture
from ckan.config.middleware import make_app
import ckan.model as model
from ckan.tests import conf_dir, url_for, CreateTestData
from ckan.controllers.admin import get_sysadmins

class TestStorageAPIController:
    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=conf_dir)
        config.local_conf['ckan.plugins'] = 'storage'
        config.local_conf['ofs.impl'] = 'pairtree'
        config.local_conf['ofs.storage_dir'] = '/tmp/ckan-test-ckanext-storage'
        wsgiapp = make_app(config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)

    def test_index(self):
        url = url_for('storage_api')
        res = self.app.get(url)
        out = res.json
        assert len(res.json) == 3

    def test_authz(self):
        url = url_for('storage_api_auth_form', label='abc')
        res = self.app.get(url, status=[200])

class TestStorageAPIControllerLocal:
    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=conf_dir)
        config.local_conf['ckan.plugins'] = 'storage'
        config.local_conf['ofs.impl'] = 'pairtree'
        config.local_conf['ofs.storage_dir'] = '/tmp/ckan-test-ckanext-storage'
        wsgiapp = make_app(config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)
        CreateTestData.create()
        model.Session.remove()
        user = model.User.by_name('tester')
        cls.extra_environ = {'Authorization': str(user.apikey)}

    @classmethod
    def teardown_class(cls):
        CreateTestData.delete()

    def test_auth_form(self):
        url = url_for('storage_api_auth_form', label='abc')
        res = self.app.get(url, extra_environ=self.extra_environ, status=200)
        assert res.json['action'] == u'http://localhost/storage/upload_handle', res.json
        assert res.json['fields'][-1]['value'] == 'abc', res

        url = url_for('storage_api_auth_form', label='abc/xxx')
        res = self.app.get(url, extra_environ=self.extra_environ, status=200)
        assert res.json['fields'][-1]['value'] == 'abc/xxx'

    def test_metadata(self):
        url = url_for('storage_api_get_metadata', label='abc')
        res = self.app.get(url, status=404)

        # TODO: test get metadata on real setup ...
        label = 'abc'
        url = url_for('storage_api_set_metadata', 
            extra_environ=self.extra_environ,
            label=label,
            data=dict(
                label=label
                )
            )
        # res = self.app.get(url, status=404)

