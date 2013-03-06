import os
import paste.fixture
from pylons import config

from ckan.config.middleware import make_app
from ckan.tests import conf_dir, url_for, CreateTestData
import ckan.model as model


class TestStorageController:
    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()
        config['ckan.storage.directory'] = '/tmp'
        wsgiapp = make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
        model.Session.remove()
        model.repo.rebuild_db()


    def test_03_authorization_wui(self):
        url = url_for('storage_upload')
        res = self.app.get(url, status=[200] )
        if res.status == 302:
            res = res.follow()
            assert 'Login' in res, res

    def test_04_index(self):
        extra_environ = {'REMOTE_USER': 'tester'}
        url = url_for('storage_upload')
        out = self.app.get(url, extra_environ=extra_environ)
        assert 'Upload' in out, out
        #assert 'action="https://commondatastorage.googleapis.com/ckan' in out, out
        #assert 'key" value="' in out, out
        #assert 'policy" value="' in out, out
        #assert 'failure_action_redirect' in out, out
        #assert 'success_action_redirect' in out, out

        url = url_for('storage_upload', filepath='xyz.txt')
        out = self.app.get(url, extra_environ=extra_environ)
        assert 'file/xyz.txt' in out, out

    # TODO: test file upload itself

