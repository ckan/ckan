# encoding: utf-8

import json
import nose
import pprint

import pylons
import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
from ckan.tests.legacy import is_datastore_supported
from ckan.lib import helpers as template_helpers

import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import extract, DatastoreFunctionalTestBase

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


class TestDatastoreInfo(DatastoreFunctionalTestBase):

    def test_info_success(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'from': 'Brazil', 'to': 'Brazil', 'num': 2},
                {'from': 'Brazil', 'to': 'Italy', 'num': 22}
            ],
        }
        result = helpers.call_action('datastore_create', **data)

        info = helpers.call_action('datastore_info', id=resource['id'])

        assert info['meta']['count'] == 2, info['meta']
        assert len(info['schema']) == 3
        assert info['schema']['to'] == 'text'
        assert info['schema']['from'] == 'text'
        assert info['schema']['num'] == 'number', info['schema']

    def test_api_info(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            id='588dfa82-760c-45a2-b78a-e3bc314a4a9b',
            package_id=dataset['id'], datastore_active=True)

        # the 'API info' is seen on the resource_read page, a snippet loaded by
        # javascript via data_api_button.html
        url = template_helpers.url_for(
            controller='api', action='snippet', ver=1,
            snippet_path='api_info.html', resource_id=resource['id'])

        app = self._get_test_app()
        page = app.get(url, status=200)

        # check we built all the urls ok
        expected_urls = (
            'http://test.ckan.net/api/3/action/datastore_create',
            'http://test.ckan.net/api/3/action/datastore_upsert',
            '<code>http://test.ckan.net/api/3/action/datastore_search',
            'http://test.ckan.net/api/3/action/datastore_search_sql',
            'http://test.ckan.net/api/3/action/datastore_search?resource_id=588dfa82-760c-45a2-b78a-e3bc314a4a9b&amp;limit=5',
            'http://test.ckan.net/api/3/action/datastore_search?q=jones&amp;resource_id=588dfa82-760c-45a2-b78a-e3bc314a4a9b',
            'http://test.ckan.net/api/3/action/datastore_search_sql?sql=SELECT * from &#34;588dfa82-760c-45a2-b78a-e3bc314a4a9b&#34; WHERE title LIKE &#39;jones&#39;',
            "url: 'http://test.ckan.net/api/3/action/datastore_search'",
            "http://test.ckan.net/api/3/action/datastore_search?resource_id=588dfa82-760c-45a2-b78a-e3bc314a4a9b&amp;limit=5&amp;q=title:jones",
        )
        for url in expected_urls:
            assert url in page, url
