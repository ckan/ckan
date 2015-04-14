from nose.tools import assert_equal

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.search.sql import PackageSearchQuery

class TestSimpleSearch:
    @classmethod
    def setup_class(cls):
        CreateTestData.create()
    
    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_get_all_entity_ids(self):
        ids = PackageSearchQuery().get_all_entity_ids()
        anna = model.Package.by_name(u'annakarenina')
        assert anna.id in ids
        assert len(ids) >= 2, len(ids)
        
    def test_run_query_basic(self):
        res = PackageSearchQuery().run({'q':'annakarenina'})
        anna = model.Package.by_name(u'annakarenina')
        assert_equal(res, {'results': [{'id': anna.id}], 'count': 1})

    def test_run_query_home(self):
        # This is the query from the CKAN home page
        res = PackageSearchQuery().run({'q': '*:*'})
        assert res['count'] >= 2, res['count']

    def test_run_query_all(self):
        # This is the default query from the search page
        res = PackageSearchQuery().run({'q': u''})
        assert res['count'] >= 2, res['count']
