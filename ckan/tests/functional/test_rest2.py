from ckan.tests.functional.test_rest import ApiTestCase
from ckan.tests.functional.test_rest import ModelApiTestCase
from ckan.tests.functional.test_rest import RelationshipsApiTestCase
from ckan.tests.functional.test_rest import SearchApiTestCase
from ckan.tests.functional.test_rest_resource_search import SearchResourceApiTestCase
from ckan.tests.functional.test_rest import MiscApiTestCase

# For CKAN API Version 2.
class Api2TestCase(ApiTestCase):
    api_version = '2'
    ref_package_by = 'id'
    ref_group_by = 'id'

    def assert_msg_represents_anna(self, msg):
        super(Api2TestCase, self).assert_msg_represents_anna(msg)
        assert 'download_url' not in msg, msg


class TestModelApi2(ModelApiTestCase, Api2TestCase):
    pass

class TestRelationshipsApi2(RelationshipsApiTestCase, Api2TestCase):
    pass

class TestSearchApi2(SearchApiTestCase, Api2TestCase):
    pass

class TestSearchResourceApi2(SearchResourceApiTestCase, Api2TestCase):
    pass

class TestMiscApi2(MiscApiTestCase, Api2TestCase):
    pass

