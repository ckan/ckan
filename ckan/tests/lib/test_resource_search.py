from webob.multidict import UnicodeMultiDict, MultiDict

from ckan.tests import *
from ckan.lib.search import get_backend, QueryOptions
from ckan import model
from ckan.lib.create_test_data import CreateTestData

class TestSearch(object):
    @classmethod
    def setup_class(self):
        if not is_search_supported():
            raise SkipTest("Search not supported")

        self.ab = 'http://site.com/a/b.txt'
        self.cd = 'http://site.com/c/d.txt'
        self.ef = 'http://site.com/e/f.txt'
        self.pkgs = [
            {'name':'pkg1',
             'resources':[
                 {'url':self.ab,
                  'description':'This is site ab.',
                  'format':'Excel spreadsheet',
                  'hash':'abc-123'},
                 {'url':self.cd,
                  'description':'This is site cd.',
                  'format':'Office spreadsheet',
                  'hash':'qwe-456'},
                 ]             
             },
            {'name':'pkg2',
             'resources':[
                 {'url':self.cd,
                  'description':'This is site cd.'},
                 {'url':self.ef,
                  'description':'This is site ef.'},
                 {'url':self.ef,
                  'description':'This is site gh.'},
                 {'url':self.ef,
                  'description':'This is site ij.'},
                 ]             
             },
            ]
        CreateTestData.create_arbitrary(self.pkgs)
        self.backend = get_backend(backend='sql')

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def res_search(self, query='', fields={}, terms=[], options=QueryOptions()):
        result = self.backend.query_for(model.PackageResource).run(query=query, fields=fields, terms=terms, options=options)
        resources = [model.Session.query(model.PackageResource).get(resource_id) for resource_id in result['results']]
        urls = set([resource.url for resource in resources])
        return urls

    def test_01_search_url(self):
        fields = {'url':'site.com'}
        result = self.backend.query_for(model.PackageResource).run(fields=fields)
        assert result['count'] == 6, result
        resources = [model.Session.query(model.PackageResource).get(resource_id) for resource_id in result['results']]
        urls = set([resource.url for resource in resources])
        assert set([self.ab, self.cd, self.ef]) == urls, urls
        
    def test_02_search_url_2(self):
        urls = self.res_search(fields={'url':'a/b'})
        assert set([self.ab]) == urls, urls

    def test_03_search_url_multiple_words(self):
        fields = UnicodeMultiDict(MultiDict(url='e'))
        fields.add('url', 'f')
        urls = self.res_search(fields=fields)
        assert set([self.ef]) == urls, urls

    def test_04_search_url_none(self):
        urls = self.res_search(fields={'url':'nothing'})
        assert set() == urls, urls
        
    def test_05_search_description(self):
        urls = self.res_search(fields={'description':'cd'})
        assert set([self.cd]) == urls, urls

    def test_06_search_format(self):
        urls = self.res_search(fields={'format':'excel'})
        assert set([self.ab]) == urls, urls

    def test_07_search_format_2(self):
        urls = self.res_search(fields={'format':'sheet'})
        assert set([self.ab, self.cd]) == urls, urls

    def test_08_search_hash_complete(self):
        urls = self.res_search(fields={'hash':'abc-123'})
        assert set([self.ab]) == urls, urls

    def test_09_search_hash_partial(self):
        urls = self.res_search(fields={'hash':'abc'})
        assert set([self.ab]) == urls, urls

    def test_10_search_hash_partial_but_not_initial(self):
        urls = self.res_search(fields={'hash':'123'})
        assert set() == urls, urls

    def test_11_search_several_fields(self):
        urls = self.res_search(fields={'description':'ab', 'format':'sheet'})
        assert set([self.ab]) == urls, urls

    def test_12_search_all_fields(self):
        fields = {'url':'a/b'}
        options = QueryOptions(all_fields=True)
        result = self.backend.query_for(model.PackageResource).run(fields=fields, options=options)
        assert result['count'] == 1, result
        res_dict = result['results'][0]
        assert isinstance(res_dict, dict)
        res_keys = set(res_dict.keys())
        expected_res_keys = model.PackageResource.get_columns() + \
                            ['id', 'package_id', 'position']
        assert res_keys == set(expected_res_keys), res_keys
        pkg1 = model.Package.by_name(u'pkg1')
        ab = pkg1.resources[0]
        assert res_dict['id'] == ab.id
        assert res_dict['package_id'] == pkg1.id
        assert res_dict['url'] == ab.url
        assert res_dict['description'] == ab.description
        assert res_dict['format'] == ab.format
        assert res_dict['hash'] == ab.hash
        assert res_dict['position'] == 0

    def test_13_pagination(self):
        # large search
        options = QueryOptions(order_by='hash')
        fields = {'url':'site'}
        all_results = self.backend.query_for(model.PackageResource).run(fields=fields, options=options)
        all_resources = all_results['results']
        all_resource_count = all_results['count']
        assert all_resource_count >= 6, all_results

        # limit
        options = QueryOptions(order_by='hash')
        options.limit = 2
        result = self.backend.query_for(model.PackageResource).run(fields=fields, options=options)
        resources = result['results']
        count = result['count']
        assert len(resources) == 2, resources
        assert count == all_resource_count
        assert resources == all_resources[:2], resources

        # offset
        options = QueryOptions(order_by='hash')
        options.limit = 2
        options.offset = 2
        result = self.backend.query_for(model.PackageResource).run(fields=fields, options=options)
        resources = result['results']
        assert len(resources) == 2, resources
        assert resources == all_resources[2:4]

        # larger offset
        options = QueryOptions(order_by='hash')
        options.limit = 2
        options.offset = 4
        result = self.backend.query_for(model.PackageResource).run(fields=fields, options=options)
        resources = result['results']
        assert len(resources) == 2, resources
        assert resources == all_resources[4:6]
