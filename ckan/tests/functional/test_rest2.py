from ckan.tests.functional.test_rest import *

class TestRest2(RestTestCase):

    api_version = '2'

    def assert_package_refs(self, res):
        assert self.anna.id in res, res
        assert self.war.id in res, res

