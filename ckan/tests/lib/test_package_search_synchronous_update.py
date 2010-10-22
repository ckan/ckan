from ckan.tests import *
import ckan.lib.search as search
from test_package_search import TestSearchOverall

class TestSearchOverallWithSynchronousIndexing(TestSearchOverall):
    '''Repeat test from test_package_search with synchronous indexing
    '''

    @classmethod
    def setup_class(self):
        import gc
        from pylons import config

        # Force a garbage collection to trigger issue #695
        gc.collect()

        config['search_backend'] = 'sql'
        self.backend = search.get_backend()
        search.setup_synchronous_indexing()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()
        search.remove_synchronous_indexing()

# Stop parent class tests from running
TestSearchOverall = None
