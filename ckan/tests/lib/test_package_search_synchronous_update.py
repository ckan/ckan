from ckan.tests import *
import ckan.lib.search as search
from test_package_search import TestSearchOverall as _TestSearchOverall


class TestSearchOverallWithSynchronousIndexing(_TestSearchOverall):
    '''Repeat test from test_package_search with synchronous indexing
    '''

    @classmethod
    def setup_class(self):
        from pylons import config
        config['search_backend'] = 'sql'
        self.backend = search.get_backend()
        search.setup_synchronous_indexing()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()
        search.remove_synchronous_indexing()


