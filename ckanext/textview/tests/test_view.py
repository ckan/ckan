# encoding: utf-8

import pytest
from ckan.common import config

from urllib.parse import urljoin

import ckan.lib.helpers as h
import ckanext.textview.plugin as plugin
from ckan.tests import factories


@pytest.mark.ckan_config('ckan.plugins', 'text_view')
@pytest.mark.ckan_config('ckan.views.default_views', '')
@pytest.mark.usefixtures("with_plugins")
class TestTextView(object):

    def test_can_view(self):
        p = plugin.TextView()
        url_same_domain = urljoin(config.get('ckan.site_url'), '/resource.txt')
        url_different_domain = 'http://some.com/resource.txt'

        data_dict = {'resource': {'format': 'jsonp',
                                  'url': url_different_domain}}
        assert p.can_view(data_dict)

        data_dict = {'resource': {'format': 'json', 'url': url_same_domain}}
        assert p.can_view(data_dict)

        data_dict = {'resource': {'format': 'xml', 'url': url_same_domain}}
        assert p.can_view(data_dict)

        data_dict = {'resource': {'format': 'txt', 'url': url_same_domain}}
        assert p.can_view(data_dict)

        data_dict = {'resource': {'format': 'foo', 'url': url_same_domain}}
        assert not p.can_view(data_dict)

        data_dict = {'resource': {'format': 'json',
                                  'url': url_different_domain}}

        assert not p.can_view(data_dict)

    @pytest.mark.usefixtures("non_clean_db", "with_request_context")
    def test_title_description_iframe_shown(self, app, create_with_upload):
        package = factories.Dataset()
        resource = create_with_upload("hello world", "file.txt", package_id=package["id"])
        resource_view = factories.ResourceView(view_type="text_view", resource_id=resource["id"])

        url = h.url_for('{}_resource.read'.format(package["type"]),
                        id=package["name"], resource_id=resource["id"])
        result = app.get(url)
        assert resource_view['title'] in result
        assert resource_view['description'] in result
        assert 'data-module="data-viewer"' in result.body

    @pytest.mark.usefixtures("non_clean_db", "with_request_context")
    def test_js_included(self, app, create_with_upload):
        package = factories.Dataset()
        resource = create_with_upload("hello world", "file.txt", package_id=package["id"])
        resource_view = factories.ResourceView(view_type="text_view", resource_id=resource["id"])

        url = h.url_for(package["type"] + '_resource.view',
                        id=package["name"], resource_id=resource["id"],
                        view_id=resource_view['id'])
        result = app.get(url)
        assert (('text_view.js' in result.body) or  # Source file
                ('textview.js' in result.body))     # Compiled file
