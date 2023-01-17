# encoding: utf-8

import pytest
import requests
import json
import responses
import six

from ckan.common import config
from ckan.tests import factories, helpers

import ckanext.resourceproxy.plugin as proxy


JSON_STRING = json.dumps({
    "a": "foo",
    "bar": "yes, I'm proxied",
    "b": 42})


@pytest.mark.ckan_config('ckan.plugins', 'resource_proxy')
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestProxyPrettyfied(object):

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, with_request_context):
        ''' We need to create the data before mocking the URLs '''
        self.url = 'http://www.ckan.org/static/example.json'
        self.dataset = factories.Dataset()
        self.resource = factories.Resource(
            package_id=self.dataset['id'],
            url=self.url
            )

    def mock_out_urls(self, *args, **kwargs):
        responses.add(responses.GET, *args, **kwargs)
        responses.add(responses.HEAD, *args, **kwargs)

    @responses.activate
    def test_resource_proxy_on_200(self):
        self.mock_out_urls(
            self.url,
            content_type='application/json',
            body=six.ensure_binary(JSON_STRING))

        url = self.resource['url']
        result = requests.get(url, timeout=30)

        assert result.status_code == 200, result.status_code
        assert "yes, I'm proxied" in six.ensure_str(result.content)

    @responses.activate
    def test_resource_proxy_on_404(self, app):
        self.mock_out_urls(
            self.url,
            body=six.ensure_binary("I'm not here"),
            content_type='application/json',
            status=404)

        url = self.resource['url']
        result = requests.get(url, timeout=30)
        assert result.status_code == 404, result.status_code

        proxied_url = proxy.get_proxified_resource_url({
            'package': self.dataset,
            'resource': self.resource
        })
        result = app.get(proxied_url)
        # we expect a 409 because the resourceproxy got an error (404)
        # from the server
        assert result.status_code == 409
        assert '404' in result.body

    @responses.activate
    def test_large_file(self, app, ckan_config):
        cl = ckan_config.get(u'ckan.resource_proxy.max_file_size') + 1
        self.mock_out_urls(
            self.url,
            headers={'Content-Length': str(cl)},
            body='c' * cl)

        proxied_url = proxy.get_proxified_resource_url({
            'package': self.dataset,
            'resource': self.resource
        })
        result = app.get(proxied_url)
        assert result.status_code == 409
        assert six.b('too large') in result.data

    @responses.activate
    def test_large_file_streaming(self, app, ckan_config):
        cl = ckan_config.get(u'ckan.resource_proxy.max_file_size') + 1
        self.mock_out_urls(
            self.url,
            stream=True,
            body='c' * cl)

        proxied_url = proxied_url = proxy.get_proxified_resource_url({
            'package': self.dataset,
            'resource': self.resource
        })
        result = app.get(proxied_url)
        assert result.status_code == 409
        assert six.b('too large') in result.data

    @responses.activate
    def test_invalid_url(self, app):
        responses.add_passthru(config['solr_url'])
        self.resource = helpers.call_action(
            'resource_patch',
            {},
            id=self.resource['id'],
            url='http:invalid_url'
        )

        proxied_url = proxied_url = proxy.get_proxified_resource_url({
            'package': self.dataset,
            'resource': self.resource
        })

        result = app.get(proxied_url)
        assert result.status_code == 409
        assert six.b('Invalid URL') in result.data

    def test_non_existent_url(self, app):
        self.resource = helpers.call_action(
            'resource_patch',
            {},
            id=self.resource['id'],
            url='http://nonexistent.example.com'
        )

        def f1():
            url = self.resource['url']
            requests.get(url, timeout=1)

        with pytest.raises(requests.ConnectionError):
            f1()

        proxied_url = proxied_url = proxy.get_proxified_resource_url({
            'package': self.dataset,
            'resource': self.resource
        })
        result = app.get(proxied_url)
        assert result.status_code == 502
        assert six.b('connection error') in result.data

    def test_proxied_resource_url_proxies_http_and_https_by_default(self):
        http_url = 'http://ckan.org'
        https_url = 'https://ckan.org'

        for url in [http_url, https_url]:
            self.resource['url'] = url
            proxied_url = proxy.get_proxified_resource_url({
                'package': self.dataset,
                'resource': self.resource
            })
            assert proxied_url != url, proxied_url

    def test_resource_url_doesnt_proxy_non_http_or_https_urls_by_default(self):
        schemes = ['file', 'ws']

        for scheme in schemes:
            url = '%s://ckan.org' % scheme
            self.resource['url'] = url
            non_proxied_url = proxied_url = proxy.get_proxified_resource_url({
                'package': self.dataset,
                'resource': self.resource
            })

            proxied_url = proxied_url = proxy.get_proxified_resource_url({
                'package': self.dataset,
                'resource': self.resource
                }, scheme
            )

            assert non_proxied_url == url, non_proxied_url
            assert proxied_url != url, proxied_url
