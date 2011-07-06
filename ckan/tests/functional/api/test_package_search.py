from nose.tools import assert_raises

from ckan.tests import is_search_supported
from ckan.tests.functional.api.base import *
from ckan.tests import TestController as ControllerTestCase
from ckan.controllers.api import ApiController
from webob.multidict import UnicodeMultiDict

class PackageSearchApiTestCase(ApiTestCase, ControllerTestCase):

    @classmethod
    def setup_class(self):
        if not is_search_supported():
            import nose
            raise nose.SkipTest
        indexer = TestSearchIndexer()
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
        self.base_url = self.offset('/search/package')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def assert_results(self, res_dict, expected_package_names):
        expected_pkgs = [self.package_ref_from_name(expected_package_name) \
                         for expected_package_name in expected_package_names]
        assert_equal(set(res_dict['results']), set(expected_pkgs))

    def package_ref_from_name(self, package_name):
        package = self.get_package_by_name(package_name)
        return self.ref_package(package)

    def test_00_read_search_params(self):
        def check(request_params, expected_params):
            params = ApiController._get_search_params(request_params)
            assert_equal(params, expected_params)
        # uri parameters
        check(UnicodeMultiDict({'q': '', 'ref': 'boris'}),
              {"q": "", "ref": "boris"})
        check(UnicodeMultiDict({'filter_by_openness': '1'}),
              {'filter_by_openness': '1'})
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

    def test_04_post_qjson(self):
        query = {'q': self.package_fixture_data['name']}
        json_query = self.dumps(query)
        offset = self.base_url
        res = self.app.post(offset, params=json_query, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, ['testpkg'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_05_uri_qjson_tags(self):
        query = {'q': 'annakarenina tags:russian tags:tolstoy'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict
        
    def test_05_uri_qjson_tags_multiple(self):
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

    def test_07_uri_qjson_tags(self):
        query = {'q': '', 'tags':['tolstoy']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_results(res_dict, [u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_multiple(self):
        query = {'q': '', 'tags':['tolstoy', 'russian']}
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

    def test_08_uri_qjson_malformed(self):
        offset = self.base_url + '?qjson="q":""' # user forgot the curly braces
        res = self.app.get(offset, status=400)
        self.assert_json_response(res, 'Bad request - Could not read parameters')
        
    def test_08_all_fields(self):
        rating = model.Rating(user_ip_address=u'123.1.2.3',
                              package=self.anna,
                              rating=3.0)
        model.Session.add(rating)
        model.repo.commit_and_remove()
        
        query = {'q': 'russian', 'all_fields':1}
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
        assert len(anna_rec['tags']) == 2, anna_rec['tags']
        for expected_tag in ['russian', 'tolstoy']:
            assert expected_tag in anna_rec['tags']
        assert anna_rec['ratings_average'] == 3.0, anna_rec['ratings_average']
        assert anna_rec['ratings_count'] == 1, anna_rec['ratings_count']

    def test_08_all_fields_syntax_error(self):
        offset = self.base_url + '?all_fields=should_be_boolean' # invalid all_fields value
        res = self.app.get(offset, status=400)
        assert('boolean' in res.body)
        assert('all_fields' in res.body)
        self.assert_json_response(res, 'boolean')

    def test_09_just_tags(self):
        offset = self.base_url + '?tags=russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict

    def test_10_multiple_tags_with_plus(self):
        offset = self.base_url + '?tags=tolstoy+russian&all_fields=1'
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
        offset = self.base_url + '?all_fields=1&tags=russian&limit=1&order_by=name'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'annakarenina', res_dict['results'][0]['name']

    def test_11_pagination_offset_limit(self):
        offset = self.base_url + '?all_fields=1&tags=russian&offset=1&limit=1&order_by=name'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'warandpeace', res_dict['results'][0]['name']

    def test_11_pagination_syntax_error(self):
        offset = self.base_url + '?all_fields=1&tags=russian&offset=should_be_integer&limit=1&order_by=name' # invalid offset value
        res = self.app.get(offset, status=400)
        assert('integer' in res.body)
        assert('offset' in res.body)
        self.assert_json_response(res, 'integer')

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

    def test_12_filter_by_openness_qjson(self):
        query = {'q': '', 'filter_by_openness': '1'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['count'], 2)
        self.assert_results(res_dict, (u'annakarenina', u'testpkg'))

    def test_12_filter_by_openness_q(self):
        offset = self.base_url + '?filter_by_openness=1'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['count'], 2)
        self.assert_results(res_dict, (u'annakarenina', u'testpkg'))

    def test_12_filter_by_openness_off_qjson(self):
        query = {'q': '', 'filter_by_openness': '0'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['count'], 3)

    def test_12_filter_by_openness_off_q(self):
        offset = self.base_url + '?filter_by_openness=0'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert_equal(res_dict['count'], 3)

    def test_13_just_groups(self):
        offset = self.base_url + '?groups=roger'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_strftimestamp(self):
        import datetime
        t = datetime.datetime(2012, 3, 4, 5, 6, 7, 890123)
        s = model.strftimestamp(t)
        assert s == "2012-03-04T05:06:07.890123", s

    def test_strptimestamp(self):
        import datetime
        s = "2012-03-04T05:06:07.890123"
        t = model.strptimestamp(s)
        assert t == datetime.datetime(2012, 3, 4, 5, 6, 7, 890123), t

class TestPackageSearchApi1(Api1TestCase, PackageSearchApiTestCase): pass
class TestPackageSearchApi2(Api2TestCase, PackageSearchApiTestCase): pass
class TestPackageSearchApiUnversioned(PackageSearchApiTestCase, ApiUnversionedTestCase): pass



