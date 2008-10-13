from ckan.model import Package
from ckan.searchquerybuilder import SearchQueryBuilder
from ckan.controllers.package import MockMode

class TestSearchQueryBuilder(object):

    def test_execute1(self):
        search_query_builder = SearchQueryBuilder(
            MockMode('package', Package, {'q': 'anna'})
        )
        search_query = search_query_builder.execute()
        search_results = search_query.all()
        assert len(search_results) == 1, search_results

        search_query_builder = SearchQueryBuilder(
            MockMode('package', Package, {'q': 'war'})
        )
        search_query = search_query_builder.execute()
        search_results = search_query.all()
        assert len(search_results) == 1, search_results

    def test_execute2(self):
        search_query_builder = SearchQueryBuilder(
            MockMode('package', Package, {'q': 'a'})
        )
        search_query = search_query_builder.execute()
        search_results = search_query.all()
        assert len(search_results) == 2, search_results

        search_query_builder = SearchQueryBuilder(
            MockMode('package', Package, {'q': 'n'})
        )
        search_query = search_query_builder.execute()
        search_results = search_query.all()
        assert len(search_results) == 2, search_results

    def test_execute0(self):
        search_query_builder = SearchQueryBuilder(
            MockMode('package', Package, {'q': 'z'})
        )
        search_query = search_query_builder.execute()
        search_results = search_query.all()
        assert len(search_results) == 0, search_results

