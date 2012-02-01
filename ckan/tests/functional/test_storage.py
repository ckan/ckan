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
        for key in config.local_conf.keys():
            if key.startswith('ofs'):
                del config.local_conf[key]
        config.local_conf['ofs.impl'] = 'pairtree'
        config.local_conf['ckan.storage.bucket'] = 'ckantest'
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
        # by default anonymous users can edit and hence upload
        res = self.app.get(url, status=[200])
        # TODO: ? test for non-authz case
        # url = url_for('storage_api_auth_form', label='abc')
        # res = self.app.get(url, status=[302,401])


class TestStorageAPIControllerLocal:
    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=conf_dir)
        for key in config.local_conf.keys():
            if key.startswith('ofs'):
                del config.local_conf[key]
        config.local_conf['ckan.storage.bucket'] = 'ckantest'
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


# Disabling because requires access to google storage to run (and this is not
# generally available to devs ...)
class _TestStorageAPIControllerGoogle:
    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=conf_dir)
        config.local_conf['ckan.storage.bucket'] = 'ckantest'
        config.local_conf['ofs.impl'] = 'google'
        if 'ofs.gs_secret_access_key' not in config.local_conf:
            raise Exception('You will need to configure access to google storage to run this test')
        # You will need these configured in your 
        # config.local_conf['ofs.gs_access_key_id'] = 'GOOGCABCDASDASD'
        # config.local_conf['ofs.gs_secret_access_key'] = '134zsdfjkw4234addad'
        # need to ensure not configured for local as breaks google setup
        # (and cannot delete all ofs keys as need the gs access codes)
        if 'ofs.storage_dir' in config.local_conf:
            del config.local_conf['ofs.storage_dir']
        wsgiapp = make_app(config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)
        # setup test data including testsysadmin user
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
        assert res.json['fields'][-1]['value'] == 'abc', res

        url = url_for('storage_api_auth_form', label='abc/xxx')
        res = self.app.get(url, extra_environ=self.extra_environ, status=200)
        assert res.json['fields'][-1]['value'] == 'abc/xxx'

        url = url_for('storage_api_auth_form', label='abc',
                success_action_redirect='abc')
        res = self.app.get(url, extra_environ=self.extra_environ, status=200)
        fields = dict([ (x['name'], x['value']) for x in res.json['fields'] ])
        assert fields['success_action_redirect'] == u'http://localhost/storage/upload/success_empty?label=abc'

    # TODO: re-enable
    # Disabling as there seems to be a mismatch between OFS and more recent
    # versions of boto (e.g. >= 2.1.1)
    # Specifically fill_in_auth method on Connection objects has gone away
    def _test_auth_request(self):
        url = url_for('storage_api_auth_request', label='abc')
        res = self.app.get(url, extra_environ=self.extra_environ, status=200)
        assert res.json['method'] == 'POST'
        assert res.json['headers']['Authorization']

