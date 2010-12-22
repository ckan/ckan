from ckan.tests import *
import ckan.lib.search as search
from ckan import plugins
from test_package_search import TestSearchOverall

class TestSearchOverallWithSynchronousIndexing(TestSearchOverall):
    '''Repeat test from test_package_search with synchronous indexing
    '''

    @classmethod
    def setup_class(self):
        if not is_search_supported():
            raise SkipTest("Search not supported")

        import gc
        from pylons import config

        # Force a garbage collection to trigger issue #695
        gc.collect()

        config['search_backend'] = 'sql'
        self.backend = search.get_backend()
        plugins.load('synchronous_search')
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()
        plugins.reset()

# Stop parent class tests from running
TestSearchOverall = None
