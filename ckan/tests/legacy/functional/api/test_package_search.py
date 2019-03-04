# encoding: utf-8

from urllib import quote

import webhelpers

import ckan.lib.search as search
from ckan.tests.legacy import setup_test_search_index
from ckan.tests.legacy.functional.api.base import *
from ckan.tests.legacy import TestController as ControllerTestCase


class PackageSearchApiTestCase(ApiTestCase, ControllerTestCase):

    @classmethod
    def setup_class(self):
        setup_test_search_index()
        CreateTestData.create()
        self.package_fixture_data = {
            'name' : u'testpkg',
            'title': 'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources': [{u'url':u'http://blahblahblah.mydomain',
                           u'format':u'', u'description':''}],
            'tags': ['russion', 'novel'],
            'license_id': u'gpl-3.0',
            'extras': {'national_statistic':'yes',
                       'geographic_coverage':'England, Wales'},
        }
        CreateTestData.create_arbitrary(self.package_fixture_data)
        self.base_url = self.offset('/action/package_search')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.clear_all()

    def assert_results(self, res_dict, expected_package_names):
        result = res_dict['result']['results'][0]
        assert_equal(result['name'], expected_package_names)

    def test_01_uri_q(self):
        offset = self.base_url + '?q=%s' % self.package_fixture_data['name']
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, 'testpkg')
        assert res_dict['result']['count'] == 1, res_dict['result']['count']

    def test_02_post_q(self):
        offset = self.base_url
        query = {'q':'testpkg'}
        res = self.app.post(offset, params=query, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, 'testpkg')
        assert res_dict['result']['count'] == 1, res_dict['result']['count']

    def test_04_post_json(self):
        query = {'q': self.package_fixture_data['name']}
        json_query = self.dumps(query)
        offset = self.base_url
        res = self.app.post(offset, params=json_query, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, 'testpkg')
        assert res_dict['result']['count'] == 1, res_dict['result']['count']

    def test_06_uri_q_tags(self):
        query = webhelpers.util.html_escape('annakarenina tags:russian tags:tolstoy')
        offset = self.base_url + '?q=%s' % query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, 'annakarenina')
        assert res_dict['result']['count'] == 1, res_dict['count']

    def test_09_just_tags(self):
        offset = self.base_url + '?q=tags:russian'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['result']['count'] == 2, res_dict

    def test_10_multiple_tags(self):
        offset = self.base_url + '?q=tags:tolstoy tags:russian'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['result']['count'] == 1, res_dict

    def test_12_all_packages_q(self):
        offset = self.base_url + '?q=""'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['result']['count'], 3)

    def test_12_all_packages_no_q(self):
        offset = self.base_url
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['result']['count'], 3)

    def test_12_filter_by_openness(self):
        offset = self.base_url + '?filter_by_openness=1'
        res = self.app.get(offset, status=400) # feature dropped in #1360
        assert "'filter_by_openness'" in res.body, res.body

    def test_12_filter_by_downloadable(self):
        offset = self.base_url + '?filter_by_downloadable=1'
        res = self.app.get(offset, status=400) # feature dropped in #1360
        assert "'filter_by_downloadable'" in res.body, res.body


class LegacyOptionsTestCase(ApiTestCase, ControllerTestCase):
    '''Here are tests with URIs in the syntax they were in
    for API v1 and v2.'''
    @classmethod
    def setup_class(self):
        setup_test_search_index()
        CreateTestData.create()
        self.package_fixture_data = {
            'name' : u'testpkg',
            'title': 'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources': [{u'url':u'http://blahblahblah.mydomain',
                           u'format':u'', u'description':''}],
            'tags': ['russion', 'novel'],
            'license_id': u'gpl-3.0',
            'extras': {'national_statistic':'yes',
                       'geographic_coverage':'England, Wales'},
        }
        CreateTestData.create_arbitrary(self.package_fixture_data)
        self.base_url = self.offset('/search/dataset')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.clear_all()

    def test_08_all_fields_syntax_error(self):
        offset = self.base_url + '?all_fields=should_be_boolean' # invalid all_fields value
        res = self.app.get(offset, status=400)
        assert('boolean' in res.body)
        assert('all_fields' in res.body)
        self.assert_json_response(res, 'boolean')

    def test_09_just_tags(self):
        offset = self.base_url + '?tags=tolstoy'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_10_single_tag_with_plus(self):
        tagname = "Flexible+" + quote(u'\u30a1'.encode('utf8'))
        offset = self.base_url + "?tags=%s&all_fields=1"%tagname
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict

    def test_10_multi_tags_with_ampersand_including_a_multiword_tagame(self):
        tagname = "Flexible+" + quote(u'\u30a1'.encode('utf8'))
        offset = self.base_url + '?tags=tolstoy&tags=%s&all_fields=1' % tagname
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_10_multiple_tags_with_ampersand(self):
        offset = self.base_url + '?tags=tolstoy&tags=russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_10_many_tags_with_ampersand(self):
        offset = self.base_url + '?tags=tolstoy&tags=russian&tags=tolstoy'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_13_just_groups(self):
        offset = self.base_url + '?groups=roger'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['result']['count'] == 1, res_dict

    def test_14_empty_parameter_ignored(self):
        offset = self.base_url + '?groups=roger&title='
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['result']['count'] == 1, res_dict


class TestPackageSearchApi3(Api3TestCase, PackageSearchApiTestCase):
    '''Here are tests with URIs in specifically SOLR syntax.'''
    def test_09_just_tags(self):
        offset = self.base_url + '?q=tags:russian&fl=*'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['result']['count'] == 2, res_dict

    def test_11_pagination_limit(self):
        offset = self.base_url + '?fl=*&q=tags:russian&rows=1&sort=name asc'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['result']['count'] == 2, res_dict
        assert len(res_dict['result']['results']) == 1, res_dict
        self.assert_results(res_dict, 'annakarenina')

    def test_11_pagination_offset_limit(self):
        offset = self.base_url + '?fl=*&q=tags:russian&start=1&rows=1&sort=name asc'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['result']['count'] == 2, res_dict
        assert len(res_dict['result']['results']) == 1, res_dict
        self.assert_results(res_dict, 'warandpeace')

    def test_11_pagination_validation_error(self):
        offset = self.base_url + '?fl=*&q=tags:russian&start=should_be_integer&rows=1&sort=name asc' # invalid offset value
        res = self.app.get(offset, status=409)
        assert('Validation Error' in res.body)

    def test_12_v1_or_v2_syntax(self):
        offset = self.base_url + '?all_fields=1'
        res = self.app.get(offset, status=400)
        assert("Invalid search parameters: ['all_fields']" in res.body), res.body

    def test_13_just_groups(self):
        offset = self.base_url + '?q=groups:roger'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['result']['count'] == 1, res_dict
