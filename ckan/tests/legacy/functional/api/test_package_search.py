# encoding: utf-8

from nose.tools import assert_raises
from nose.plugins.skip import SkipTest

from urllib import quote

from ckan import plugins
import ckan.lib.search as search
from ckan.tests.legacy import setup_test_search_index
from ckan.tests.legacy.functional.api.base import *
from ckan.tests.legacy import TestController as ControllerTestCase
from ckan.controllers.api import ApiController
from webob.multidict import UnicodeMultiDict

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
        self.base_url = self.offset('/search/dataset')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.clear_all()

    def assert_results(self, res_dict, expected_package_names):
        expected_pkgs = [self.package_ref_from_name(expected_package_name) \
                         for expected_package_name in expected_package_names]
        assert_equal(set(res_dict['results']), set(expected_pkgs))

    def test_00_read_search_params(self):
        def check(request_params, expected_params):
            params = ApiController._get_search_params(request_params)
            assert_equal(params, expected_params)
        # uri parameters
        check(UnicodeMultiDict({'q': '', 'ref': 'boris'}),
              {"q": "", "ref": "boris"})
        # uri json
        check(UnicodeMultiDict({'qjson': '{"q": "", "ref": "boris"}'}),
              {"q": "", "ref": "boris"})
        # posted json
        check(UnicodeMultiDict({'{"q": "", "ref": "boris"}': u'1'}),
              {"q": "", "ref": "boris"})
        check(UnicodeMultiDict({'{"q": "", "ref": "boris"}': u''}),
              {"q": "", "ref": "boris"})
        # no parameters
        check(UnicodeMultiDict({}),
              {})

    def test_00_read_search_params_with_errors(self):
        def check_error(request_params):
            assert_raises(ValueError, ApiController._get_search_params, request_params)
        # uri json
        check_error(UnicodeMultiDict({'qjson': '{"q": illegal json}'}))
        # posted json
        check_error(UnicodeMultiDict({'{"q": illegal json}': u'1'}))

    def test_01_uri_q(self):
        offset = self.base_url + '?q=%s' % self.package_fixture_data['name']
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, ['testpkg'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_02_post_q(self):
        offset = self.base_url
        query = {'q':'testpkg'}
        res = self.app.post(offset, params=query, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, ['testpkg'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_03_uri_qjson(self):
        query = {'q': self.package_fixture_data['name']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, ['testpkg'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_04_post_json(self):
        query = {'q': self.package_fixture_data['name']}
        json_query = self.dumps(query)
        offset = self.base_url
        res = self.app.post(offset, params=json_query, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, ['testpkg'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_05_uri_json_tags(self):
        query = {'q': 'annakarenina tags:russian tags:tolstoy'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_05_uri_json_tags_multiple(self):
        query = {'q': 'tags:russian tags:tolstoy'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_06_uri_q_tags(self):
        query = webhelpers.util.html_escape('annakarenina tags:russian tags:tolstoy')
        offset = self.base_url + '?q=%s' % query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_08_uri_qjson_malformed(self):
        offset = self.base_url + '?qjson="q":""' # user forgot the curly braces
        res = self.app.get(offset, status=400)
        self.assert_json_response(res, 'Bad request - Could not read parameters')

    def test_09_just_tags(self):
        offset = self.base_url + '?q=tags:russian'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict

    def test_10_multiple_tags(self):
        offset = self.base_url + '?q=tags:tolstoy tags:russian'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_12_all_packages_qjson(self):
        query = {'q': ''}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['count'], 3)

    def test_12_all_packages_q(self):
        offset = self.base_url + '?q=""'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['count'], 3)

    def test_12_all_packages_no_q(self):
        offset = self.base_url
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['count'], 3)

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

    def test_07_uri_qjson_tags(self):
        query = {'q': '', 'tags':['tolstoy']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_with_flexible_query(self):
        query = {'q': '', 'tags':['Flexible \u30a1']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina', u'warandpeace'])
        assert res_dict['count'] == 2, res_dict

    def test_07_uri_qjson_tags_multiple(self):
        query = {'q': '', 'tags':['tolstoy', 'russian', u'Flexible \u30a1']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        print offset
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_reverse(self):
        query = {'q': '', 'tags':['russian']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina', u'warandpeace'])
        assert res_dict['count'] == 2, res_dict

    def test_07_uri_qjson_extras(self):
        # TODO: solr is not currently set up to allow partial matches
        #       and extras are not saved as multivalued so this
        #       test will fail. Make extras multivalued or remove?
        raise SkipTest()

        query = {"geographic_coverage":"England"}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, ['testpkg'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_extras_2(self):
        query = {"national_statistic":"yes"}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, ['testpkg'])
        assert res_dict['count'] == 1, res_dict

    def test_08_all_fields(self):
        rating = model.Rating(user_ip_address=u'123.1.2.3',
                              package=self.anna,
                              rating=3.0)
        model.Session.add(rating)
        model.repo.commit_and_remove()

        query = {'q': 'russian', 'all_fields': 1}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        for rec in res_dict['results']:
            if rec['name'] == 'annakarenina':
                anna_rec = rec
                break
        assert anna_rec['name'] == 'annakarenina', res_dict['results']
        assert anna_rec['title'] == 'A Novel By Tolstoy', anna_rec['title']
        assert anna_rec['license_id'] == u'other-open', anna_rec['license_id']
        assert len(anna_rec['tags']) == 3, anna_rec['tags']
        for expected_tag in ['russian', 'tolstoy', u'Flexible \u30a1']:
            assert expected_tag in anna_rec['tags'], anna_rec['tags']

        # try alternative syntax
        offset = self.base_url + '?q=russian&all_fields=1'
        res2 = self.app.get(offset, status=200)
        assert_equal(res2.body, res.body)

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

    def test_11_pagination_limit(self):
        offset = self.base_url + '?all_fields=1&q=tags:russian&limit=1&order_by=name'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'annakarenina', res_dict['results'][0]['name']

    def test_11_pagination_offset_limit(self):
        offset = self.base_url + '?all_fields=1&q=tags:russian&offset=1&limit=1&order_by=name'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'warandpeace', res_dict['results'][0]['name']

    def test_11_pagination_syntax_error(self):
        offset = self.base_url + '?all_fields=1&q="tags:russian"&start=should_be_integer&rows=1&order_by=name' # invalid offset value
        res = self.app.get(offset, status=400)
        print res.body
        assert('should_be_integer' in res.body)

    def test_13_just_groups(self):
        offset = self.base_url + '?groups=roger'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_14_empty_parameter_ignored(self):
        offset = self.base_url + '?groups=roger&title='
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

class TestPackageSearchApi1(Api1TestCase, PackageSearchApiTestCase,
                            LegacyOptionsTestCase): pass
class TestPackageSearchApi2(Api2TestCase, PackageSearchApiTestCase,
                            LegacyOptionsTestCase): pass
class TestPackageSearchApi3(Api3TestCase, PackageSearchApiTestCase):
    '''Here are tests with URIs in specifically SOLR syntax.'''
    def test_07_uri_qjson_tags(self):
        query = {'q': 'tags:tolstoy'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_with_unicode(self):
        query = {'q': u'tags:"Flexible \u30a1"'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina', u'warandpeace'])
        assert res_dict['count'] == 2, res_dict

    def test_07_uri_qjson_tags_multiple(self):
        query = {'q': 'tags:tolstoy tags:russian'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        print offset
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_reverse(self):
        query = {'q': 'tags:russian'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina', u'warandpeace'])
        assert res_dict['count'] == 2, res_dict

    def test_07_uri_qjson_extras_2(self):
        query = {'q': "national_statistic:yes"}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, ['testpkg'])
        assert res_dict['count'] == 1, res_dict

    def test_08_all_fields(self):
        query = {'q': 'russian', 'fl': '*'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        for rec in res_dict['results']:
            if rec['name'] == 'annakarenina':
                anna_rec = rec
                break
        assert anna_rec['name'] == 'annakarenina', res_dict['results']
        assert anna_rec['title'] == 'A Novel By Tolstoy', anna_rec['title']
        assert anna_rec['license_id'] == u'other-open', anna_rec['license_id']
        assert len(anna_rec['tags']) == 3, anna_rec['tags']
        for expected_tag in ['russian', 'tolstoy', u'Flexible \u30a1']:
            assert expected_tag in anna_rec['tags']

        # try alternative syntax
        offset = self.base_url + '?q=russian&fl=*'
        res2 = self.app.get(offset, status=200)
        assert_equal(res2.body, res.body)

    def test_09_just_tags(self):
        offset = self.base_url + '?q=tags:russian&fl=*'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict

    def test_11_pagination_limit(self):
        offset = self.base_url + '?fl=*&q=tags:russian&rows=1&sort=name asc'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'annakarenina', res_dict['results'][0]['name']

    def test_11_pagination_offset_limit(self):
        offset = self.base_url + '?fl=*&q=tags:russian&start=1&rows=1&sort=name asc'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'warandpeace', res_dict['results'][0]['name']

    def test_11_pagination_syntax_error(self):
        offset = self.base_url + '?fl=*&q=tags:russian&start=should_be_integer&rows=1&sort=name asc' # invalid offset value
        res = self.app.get(offset, status=400)
        print res.body
        assert('should_be_integer' in res.body)

    def test_12_v1_or_v2_syntax(self):
        offset = self.base_url + '?all_fields=1'
        res = self.app.get(offset, status=400)
        assert("Invalid search parameters: ['all_fields']" in res.body), res.body

    def test_13_just_groups(self):
        offset = self.base_url + '?q=groups:roger'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict
