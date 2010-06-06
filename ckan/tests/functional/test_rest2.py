from ckan.tests.functional.test_rest import *

# For CKAN API Version 2.
class TestRest2(RestTestCase):

    api_version = '2'

    def assert_package_refs(self, res):
        assert self.anna.id in res, res
        assert self.war.id in res, res

    def assert_revision_packages(self, packages):
        assert isinstance(packages, list)
        assert len(packages) != 0, "Revision packages is empty: %s" % packages
        package = self.get_package_by_name(self.fixture_package_name)
        assert package.id in packages, (package.id, packages)


# For CKAN API Version 2.
class TestSearch2(BaseSearchCase):

    api_version = '2'

    def assert_package_search_results(self, results, names=[u'testpkg']):
        for name in names:
            package = self.get_package_by_name(name)
            assert package.id in results, (package.id, results)

