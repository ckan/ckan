# encoding: utf-8

from webob.multidict import UnicodeMultiDict, MultiDict
from nose.tools import assert_raises, assert_equal

from ckan.tests.legacy import *
from ckan.tests.legacy import is_search_supported
import ckan.lib.search as search
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
                  'hash':'xyz-123',
                  'alt_url': 'alt_1',
                  'extras':{'size_extra': '100'},
                  },
                 {'url':self.cd,
                  'description':'This is site cd.',
                  'format':'Office spreadsheet',
                  'hash':'qwe-456',
                  'alt_url':'alt_2',
                  'extras':{'size_extra':'200'},
                  },
                 ]
             },
            {'name':'pkg2',
             'resources':[
                 {'url':self.cd,
                  'alt_url': 'alt_1',
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

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def res_search(self, query='', fields={}, terms=[], options=search.QueryOptions()):
        result = search.query_for(model.Resource).run(query=query, fields=fields, terms=terms, options=options)
        resources = [model.Session.query(model.Resource).get(resource_id) for resource_id in result['results']]
        urls = set([resource.url for resource in resources])
        return urls

    def test_01_search_url(self):
        fields = {'url':'site.com'}
        result = search.query_for(model.Resource).run(fields=fields)
        assert result['count'] == 6, result
        resources = [model.Session.query(model.Resource).get(resource_id) for resource_id in result['results']]
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
        urls = self.res_search(fields={'hash':'xyz-123'})
        assert set([self.ab]) == urls, urls

    def test_09_search_hash_partial(self):
        urls = self.res_search(fields={'hash':'xyz'})
        assert set([self.ab]) == urls, urls

    def test_10_search_hash_partial_but_not_initial(self):
        urls = self.res_search(fields={'hash':'123'})
        assert set() == urls, urls

    def test_11_search_several_fields(self):
        urls = self.res_search(fields={'description':'ab', 'format':'sheet'})
        assert set([self.ab]) == urls, urls

    def test_12_search_all_fields(self):
        fields = {'url':'a/b'}
        options = search.QueryOptions(all_fields=True)
        result = search.query_for(model.Resource).run(fields=fields, options=options)
        assert result['count'] == 1, result
        res_dict = result['results'][0]
        assert isinstance(res_dict, dict)
        res_keys = set(res_dict.keys())
        expected_res_keys = set(model.Resource.get_columns())
        expected_res_keys.update(['id', 'package_id', 'position', 'size_extra'])
        assert_equal(res_keys, expected_res_keys)
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
        options = search.QueryOptions(order_by='id')
        fields = {'url':'site'}
        all_results = search.query_for(model.Resource).run(fields=fields, options=options)
        all_resources = all_results['results']
        all_resource_count = all_results['count']
        assert all_resource_count >= 6, all_results

        # limit
        options = search.QueryOptions(order_by='id')
        options.limit = 2
        result = search.query_for(model.Resource).run(fields=fields, options=options)
        resources = result['results']
        count = result['count']
        assert len(resources) == 2, resources
        assert count == all_resource_count, (count, all_resource_count)
        assert resources == all_resources[:2], '%r, %r' % (resources, all_resources)

        # offset
        options = search.QueryOptions(order_by='id')
        options.limit = 2
        options.offset = 2
        result = search.query_for(model.Resource).run(fields=fields, options=options)
        resources = result['results']
        assert len(resources) == 2, resources
        assert resources == all_resources[2:4]

        # larger offset
        options = search.QueryOptions(order_by='id')
        options.limit = 2
        options.offset = 4
        result = search.query_for(model.Resource).run(fields=fields, options=options)
        resources = result['results']
        assert len(resources) == 2, resources
        assert resources == all_resources[4:6]

    def test_14_extra_info(self):
        fields = {'alt_url':'alt_1'}
        result = search.query_for(model.Resource).run(fields=fields)
        assert result['count'] == 2, result

        fields = {'alt_url':'alt_2'}
        result = search.query_for(model.Resource).run(fields=fields)
        assert result['count'] == 1, result

        # Document that resource extras not in ckan.extra_resource_fields
        # can't be searched
        fields = {'size_extra':'100'}
        assert_raises(search.SearchError, search.query_for(model.Resource).run, fields=fields)
