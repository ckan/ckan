import requests
import unittest
import json
import httpretty

import paste.fixture
from pylons import config

import ckan.logic as logic
import ckan.model as model
import ckan.tests as tests
import ckan.plugins as plugins
import ckan.lib.create_test_data as create_test_data
import ckan.config.middleware as middleware
import ckanext.resourceproxy.controller as controller

import ckanext.resourceproxy.plugin as proxy


JSON_STRING = json.dumps({
    "a": "foo",
    "bar": "yes, I'm proxied",
    "b": 42})


def set_resource_url(url):
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

    return {'resource': resource, 'package': package}


class TestProxyPrettyfied(tests.WsgiAppCase, unittest.TestCase):

    serving = False

    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()
        config['ckan.plugins'] = 'resource_proxy'
        wsgiapp = middleware.make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)

        # create test resource
        create_test_data.CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
        model.repo.rebuild_db()

    def setUp(self):
        self.url = 'http://www.ckan.org/static/example.json'
        self.data_dict = set_resource_url(self.url)

    def register(self, *args, **kwargs):
        httpretty.HTTPretty.register_uri(httpretty.HTTPretty.GET, *args, **kwargs)
        httpretty.HTTPretty.register_uri(httpretty.HTTPretty.HEAD, *args, **kwargs)

    @httpretty.activate
    def test_resource_proxy_on_200(self):
        self.register(
            self.url,
            content_type='application/json',
            body=JSON_STRING)

        url = self.data_dict['resource']['url']
        result = requests.get(url)
        assert result.status_code == 200, result.status_code
        assert "yes, I'm proxied" in result.content, result.content

    @httpretty.activate
    def test_resource_proxy_on_404(self):
        self.register(
            self.url,
            body="I'm not here",
            content_type='application/json',
            status=404)

        url = self.data_dict['resource']['url']
        result = requests.get(url)
        assert result.status_code == 404, result.status_code

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        # we expect a 409 because the resourceproxy got an error (404)
        # from the server
        assert result.status == 409, result.status
        assert '404' in result.body

    @httpretty.activate
    def test_large_file(self):
        cl = controller.MAX_FILE_SIZE + 1
        self.register(
            self.url,
            content_length=cl,
            body='c' * cl)

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 409, result.status
        assert 'too large' in result.body, result.body

    @httpretty.activate
    def test_large_file_streaming(self):
        cl = controller.MAX_FILE_SIZE + 1
        self.register(
            self.url,
            streaming=True,
            body='c' * cl)

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 409, result.status
        assert 'too large' in result.body, result.body

    @httpretty.activate
    def test_invalid_url(self):
        self.data_dict = set_resource_url('javascript:downloadFile(foo)')

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 409, result.status
        assert 'Invalid URL' in result.body, result.body


    def test_non_existent_url(self):
        self.data_dict = set_resource_url('http://foo.bar')

        def f1():
            url = self.data_dict['resource']['url']
            requests.get(url)
        self.assertRaises(requests.ConnectionError, f1)

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = self.app.get(proxied_url, status='*')
        assert result.status == 502, result.status
        assert 'connection error' in result.body, result.body
