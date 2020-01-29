# encoding: utf-8

import pytest
import requests
import json
import responses
import six

from ckan.tests.helpers import _get_test_app
from ckan.common import config

import ckan.model as model
import ckan.plugins as p
import ckan.lib.create_test_data as create_test_data
import ckanext.resourceproxy.blueprint as blueprint
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
        'user': model.User.get('testsysadmin').name,
        'use_cache': False,
    }

    resource = p.toolkit.get_action('resource_show')(
        context, {'id': testpackage.resources[0].id})
    package = p.toolkit.get_action('package_show')(
        context, {'id': testpackage.id})

    resource['url'] = url
    p.toolkit.get_action('resource_update')(context, resource)

    testpackage = model.Package.get('annakarenina')
    assert testpackage.resources[0].url == resource['url']

    return {'resource': resource, 'package': package}


@pytest.mark.ckan_config('ckan.plugins', 'resource_proxy')
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestProxyPrettyfied(object):

    serving = False

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, with_request_context):
        create_test_data.CreateTestData.create()
        self.url = 'http://www.ckan.org/static/example.json'
        self.data_dict = set_resource_url(self.url)

    def mock_out_urls(self, *args, **kwargs):
        responses.add(responses.GET, *args, **kwargs)
        responses.add(responses.HEAD, *args, **kwargs)

    @responses.activate
    def test_resource_proxy_on_200(self):
        self.mock_out_urls(
            self.url,
            content_type='application/json',
            body=six.ensure_binary(JSON_STRING))

        url = self.data_dict['resource']['url']
        result = requests.get(url)
        assert result.status_code == 200, result.status_code
        assert "yes, I'm proxied" in six.ensure_str(result.content)

    @responses.activate
    def test_resource_proxy_on_404(self, app):
        self.mock_out_urls(
            self.url,
            body=six.ensure_binary("I'm not here"),
            content_type='application/json',
            status=404)

        url = self.data_dict['resource']['url']
        result = requests.get(url)
        assert result.status_code == 404, result.status_code

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = app.get(proxied_url)
        # we expect a 409 because the resourceproxy got an error (404)
        # from the server
        assert result.status_code == 409
        assert '404' in result.body

    @responses.activate
    def test_large_file(self, app):
        cl = blueprint.MAX_FILE_SIZE + 1
        self.mock_out_urls(
            self.url,
            headers={'Content-Length': six.text_type(cl)},
            body='c' * cl)

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = app.get(proxied_url)
        assert result.status_code == 409
        assert six.b('too large') in result.data

    @responses.activate
    def test_large_file_streaming(self, app):
        cl = blueprint.MAX_FILE_SIZE + 1
        self.mock_out_urls(
            self.url,
            stream=True,
            body='c' * cl)

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = app.get(proxied_url)
        assert result.status_code == 409
        assert six.b('too large') in result.data

    @responses.activate
    def test_invalid_url(self, app):
        responses.add_passthru(config['solr_url'])
        self.data_dict = set_resource_url('http:invalid_url')

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = app.get(proxied_url)
        assert result.status_code == 409
        assert six.b('Invalid URL') in result.data

    def test_non_existent_url(self, app):
        self.data_dict = set_resource_url('http://nonexistent.example.com')

        def f1():
            url = self.data_dict['resource']['url']
            requests.get(url)

        with pytest.raises(requests.ConnectionError):
            f1()

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = app.get(proxied_url)
        assert result.status_code == 502
        assert six.b('connection error') in result.data

    def test_proxied_resource_url_proxies_http_and_https_by_default(self):
        http_url = 'http://ckan.org'
        https_url = 'https://ckan.org'

        for url in [http_url, https_url]:
            data_dict = set_resource_url(url)
            proxied_url = proxy.get_proxified_resource_url(data_dict)
            assert proxied_url != url, proxied_url

    def test_resource_url_doesnt_proxy_non_http_or_https_urls_by_default(self):
        schemes = ['file', 'ws']

        for scheme in schemes:
            url = '%s://ckan.org' % scheme
            data_dict = set_resource_url(url)
            non_proxied_url = proxy.get_proxified_resource_url(data_dict)
            proxied_url = proxy.get_proxified_resource_url(data_dict, scheme)
            assert non_proxied_url == url, non_proxied_url
            assert proxied_url != url, proxied_url
