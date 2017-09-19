# encoding: utf-8

from ckan.tests.legacy.functional.api.base import ApiTestCase, CreateTestData
from ckan.tests.legacy import TestController as ControllerTestCase
from ckan import model

class TestResourceApi(ApiTestCase, ControllerTestCase):
    api_version = '2'

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
                 'format':'CSV',
                 'alt_url':'alt',
                 'extras':{'size':'100'},
                 'hash':'qwe-456'},
                ],
            'tags': ['russian', 'novel'],
            'license_id': u'gpl-3.0',
            'extras': {'national_statistic':'yes',
                       'geographic_coverage':'England, Wales'},
        }
        CreateTestData.create_arbitrary(self.package_fixture_data)
        self.base_url = self.offset('/util/resource')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_good_input(self):
        offset = self.base_url + '/format_autocomplete?incomplete=cs'
        result = self.app.get(offset, status=200)
        content_type = result.header_dict['Content-Type']
        assert 'application/json' in content_type, content_type
        res_json = self.loads(result.body)
        assert 'ResultSet' in res_json, res_json
        assert 'Result' in res_json.get('ResultSet'), res_json
        result_json = res_json.get('ResultSet').get('Result')
        assert len(result_json) == 1, result_json
        assert 'Format' in result_json[0], result_json
        assert result_json[0].get('Format') == 'csv'

    def test_missing_format(self):
        offset = self.base_url + '/format_autocomplete?incomplete=incorrectformat'
        result = self.app.get(offset, status=200)
        content_type = result.header_dict['Content-Type']
        assert 'application/json' in content_type, content_type
        res_json = self.loads(result.body)
        assert 'ResultSet' in res_json, res_json
        assert 'Result' in res_json.get('ResultSet'), res_json
        result_json = res_json.get('ResultSet').get('Result')
        assert not result_json, result_json
