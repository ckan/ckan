import requests
import unittest

import paste.fixture
from pylons import config

import ckan.logic as logic
import ckan.model as model
import ckan.tests as tests
import ckan.plugins as plugins
import ckan.lib.create_test_data as create_test_data
import ckan.config.middleware as middleware

import ckanext.resourceproxy.plugin as proxy
import file_server


class TestProxyBasic(tests.WsgiAppCase, unittest.TestCase):

    serving = False

    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()
        config['ckan.plugins'] = 'resource_proxy'
        wsgiapp = middleware.make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)

        if not cls.serving:
            file_server.serve()
            cls.serving = True
            # gets shutdown when nose finishes all tests,
            # so don't restart ever

        # create test resource
        create_test_data.CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
        model.repo.rebuild_db()
        plugins.reset()

    def set_resource_url(self, url):
        testpackage = model.Package.get('annakarenina')

        context = {
            'model': model,
            'session': model.Session,
            'user': model.User.get('testsysadmin').name
        }

        resource = logic.get_action('resource_show')(context, {'id': testpackage.resources[0].id})
        package = logic.get_action('package_show')(context, {'id': testpackage.id})

        resource['url'] = url
        logic.action.update.resource_update(context, resource)

        testpackage = model.Package.get('annakarenina')
        assert testpackage.resources[0].url == resource['url'], testpackage.resources[0].url

        self.data_dict = {'resource': resource, 'package': package}

    def test_resource_proxy_on_200(self):
        self.set_resource_url('http://0.0.0.0:50001/test.json')

        url = self.data_dict['resource']['url']
        result = requests.get(url)
        assert result.status_code == 200, result.status_code
        assert "yes, I'm proxied" in result.content, result.content

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 200, result.status
        assert "yes, I'm proxied" in result.body, result.body

    def test_resource_proxy_on_404(self):
        self.set_resource_url('http://0.0.0.0:50001/foo.bar')

        url = self.data_dict['resource']['url']
        result = requests.get(url)
        assert result.status_code == 404, result.status_code

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 404, result.status

    def test_large_file(self):
        self.set_resource_url('http://0.0.0.0:50001/huge.json')

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 500, result.status
        assert 'too large' in result.body, result.body

    def test_resource_proxy_non_existent(self):
        self.set_resource_url('http://foo.bar')

        def f1():
            url = self.data_dict['resource']['url']
            requests.get(url)
        self.assertRaises(requests.ConnectionError, f1)

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 500, result.status
        assert 'connection error' in result.body, result.body
