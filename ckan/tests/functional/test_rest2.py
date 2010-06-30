from ckan.tests.functional.test_rest import ApiTestCase
from ckan.tests.functional.test_rest import ModelApiTestCase
from ckan.tests.functional.test_rest import RelationshipsApiTestCase
from ckan.tests.functional.test_rest import SearchApiTestCase
from ckan.tests.functional.test_rest import MiscApiTestCase

# For CKAN API Version 2.
class Api2TestCase(ApiTestCase):
    api_version = '2'
    ref_package_with_attr = 'id'

class TestModelApi2(ModelApiTestCase, Api2TestCase):
    pass

class TestRelationshipsApi2(RelationshipsApiTestCase, Api2TestCase):
    pass

class TestSearchApi2(SearchApiTestCase, Api2TestCase):
    pass

class TestMiscApi2(MiscApiTestCase, Api2TestCase):
    pass

