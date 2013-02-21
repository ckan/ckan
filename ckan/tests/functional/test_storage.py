import os

import paste.fixture
import pylons.config as config

import ckan.model as model
from ckan.config.middleware import make_app
from ckan.tests import conf_dir, url_for, CreateTestData
from ckan.controllers.admin import get_sysadmins
from ckan.controllers.storage import create_pairtree_marker


class TestStorageAPIController:
    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()
        for key in config.keys():
            if key.startswith('ofs'):
                del config[key]
        config['ofs.impl'] = 'pairtree'
        config['ckan.storage.bucket'] = 'ckantest'
        config['ofs.storage_dir'] = '/tmp/ckan-test-ckanext-storage'

        create_pairtree_marker( config['ofs.storage_dir'] )
        wsgiapp = make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)

        CreateTestData.create_test_user()

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
        CreateTestData.delete()

    def test_index(self):
        url = url_for('storage_api')
        res = self.app.get(url)
        out = res.json
        assert len(res.json) == 3

    def test_authz(self):
        url = url_for('storage_api_auth_form', label='abc')

        # Non logged in users can not upload
        res = self.app.get(url, status=[302,401])

        # Logged in users can upload
        res = self.app.get(url, status=[200], extra_environ={'REMOTE_USER':'tester'})


        # TODO: ? test for non-authz case
        # url = url_for('storage_api_auth_form', label='abc')
        # res = self.app.get(url, status=[302,401])


class TestStorageAPIControllerLocal:
    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()
        for key in config.keys():
            if key.startswith('ofs'):
                del config[key]
        config['ckan.storage.bucket'] = 'ckantest'
        config['ofs.impl'] = 'pairtree'
        config['ofs.storage_dir'] = '/tmp/ckan-test-ckanext-storage'
        create_pairtree_marker( config['ofs.storage_dir'] )
        wsgiapp = make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)
        CreateTestData.create()
        model.Session.remove()
        user = model.User.by_name('tester')
        cls.extra_environ = {'Authorization': str(user.apikey)}

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
        CreateTestData.delete()

    def test_auth_form(self):
        url = url_for('storage_api_auth_form', label='abc')
        res = self.app.get(url, extra_environ=self.extra_environ, status=200)
        assert res.json['action'] == u'/storage/upload_handle', res.json
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
        cls._original_config = config.copy()
        config['ckan.storage.bucket'] = 'ckantest'
        config['ofs.impl'] = 'google'
        if 'ofs.gs_secret_access_key' not in config:
            raise Exception('You will need to configure access to google storage to run this test')
        # You will need these configured in your
        # config['ofs.gs_access_key_id'] = 'GOOGCABCDASDASD'
        # config['ofs.gs_secret_access_key'] = '134zsdfjkw4234addad'
        # need to ensure not configured for local as breaks google setup
        # (and cannot delete all ofs keys as need the gs access codes)
        if 'ofs.storage_dir' in config:
            del config['ofs.storage_dir']
        wsgiapp = make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)
        # setup test data including testsysadmin user
        CreateTestData.create()
        model.Session.remove()
        user = model.User.by_name('tester')
        cls.extra_environ = {'Authorization': str(user.apikey)}

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
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

