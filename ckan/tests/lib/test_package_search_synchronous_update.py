from ckan.tests import *
import ckan.model as model
from test_package_search import TestSearchOverall as _TestSearchOverall


class TestSearchOverallWithSynchronousIndexing(_TestSearchOverall):
    '''Repeat test from test_package_search with synchronous indexing
    '''

    @classmethod
    def setup_class(self):
        model.setup_synchronous_indexing()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()
        model.remove_synchronous_indexing()

