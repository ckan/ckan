import os
import subprocess
import requests
import time
import unittest

import paste.fixture
from paste.deploy import appconfig

import ckan.logic as logic
import ckan.model as model
import ckan.tests as tests
import ckan.plugins as plugins
import ckan.lib.create_test_data as create_test_data
import ckan.config.middleware as middleware

import ckanext.resourceproxy.plugin as proxy


class TestProxyBasic(tests.WsgiAppCase, unittest.TestCase):

    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=tests.conf_dir)
        config.local_conf['ckan.plugins'] = 'resource_proxy'
        wsgiapp = middleware.make_app(config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)

        static_files_server = os.path.join(os.path.dirname(__file__),
                                           'file_server.py')
        cls.static_files_server = subprocess.Popen(
            ['python', static_files_server])

        # create test resource
        create_test_data.CreateTestData.create()

        #make sure services are running
        for i in range(0, 50):
            time.sleep(0.1)
            response = requests.get('http://0.0.0.0:50001')
            if not response:
                continue
            return

        cls.teardown_class()
        raise Exception('services did not start!')

    @classmethod
    def teardown_class(cls):
        cls.static_files_server.kill()
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
        self.set_resource_url('http://0.0.0.0:50001/static/test.json')

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

    def test_resource_proxy_non_existent(self):
        self.set_resource_url('http://foo.bar')

        def f1():
            url = self.data_dict['resource']['url']
            requests.get(url)
        self.assertRaises(requests.ConnectionError, f1)

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 500, result.status
        assert 'Could not proxy resource' in result.body, result.body
