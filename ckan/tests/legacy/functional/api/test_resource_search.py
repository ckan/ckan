# encoding: utf-8

from ckan.tests.legacy.functional.api.base import *
from ckan.tests.legacy import TestController as ControllerTestCase

class ResourceSearchApiTestCase(ApiTestCase, ControllerTestCase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.ab = 'http://site.com/a/b.txt'
        self.cd = 'http://site.com/c/d.txt'
        self.package_fixture_data = {
            'name' : u'testpkg',
            'title': 'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources':[
                {'url':self.ab,
                 'description':'This is site ab.',
                 'format':'Excel spreadsheet',
                 'alt_url':'alt',
                 'extras':{'size':'100'},
                 'hash':'abc-123'},
                {'url':self.cd,
                 'description':'This is site cd.',
                 'format':'Office spreadsheet',
                 'alt_url':'alt',
                 'extras':{'size':'100'},
                 'hash':'qwe-456'},
                ],
            'tags': ['russion', 'novel', 'Leo Tolstoy'],
            'license_id': u'gpl-3.0',
            'extras': {'national_statistic':'yes',
                       'geographic_coverage':'England, Wales'},
        }
        CreateTestData.create_arbitrary(self.package_fixture_data)
        self.base_url = self.offset('/search/resource')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def assert_urls_in_search_results(self, offset, expected_urls):
        result = self.app.get(offset, status=200)
        result_dict = self.loads(result.body)
        resources = [model.Session.query(model.Resource).get(resource_id) for resource_id in result_dict['results']]
        urls = set([resource.url for resource in resources])
        assert urls == set(expected_urls), urls

    def test_01_url(self):
        offset = self.base_url + '?url=site'
        self.assert_urls_in_search_results(offset, [self.ab, self.cd])

    def test_02_url_qjson(self):
        query = {'url':'site'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        self.assert_urls_in_search_results(offset, [self.ab, self.cd])

    def test_03_post_qjson(self):
        query = {'url':'site'}
        json_query = self.dumps(query)
        offset = self.base_url
        result = self.app.post(offset, params=json_query, status=200)
        expected_urls = [self.ab, self.cd]
        result_dict = self.loads(result.body)
        resources = [model.Session.query(model.Resource).get(resource_id) for resource_id in result_dict['results']]
        urls = set([resource.url for resource in resources])
        assert urls == set(expected_urls), urls

    def test_04_bad_option(self):
        offset = self.base_url + '?random=option'
        result = self.app.get(offset, status=400)
        self.assert_json_response(result, 'Bad request - Bad search option')

    def test_05_options(self):
        offset = self.base_url + '?url=site&all_fields=1&callback=mycallback'
        result = self.app.get(offset, status=200)
        assert re.match('^mycallback\(.*\);$', result.body), result.body
        assert 'package_id' in result.body, result.body
