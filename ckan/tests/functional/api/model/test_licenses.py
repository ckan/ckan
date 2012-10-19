from nose.tools import assert_equal 

from ckan import model
from ckan.lib.create_test_data import CreateTestData

from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase 
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase 
from ckan.tests.functional.api.base import ApiUnversionedTestCase as UnversionedTestCase 

class LicensesTestCase(BaseModelApiTestCase):

    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_register_get_ok(self):
        from ckan.model.license import LicenseRegister
        register = LicenseRegister()
        assert len(register), "No changesets found in model."
        offset = self.offset('/rest/licenses')
        res = self.app.get(offset, status=[200])
        licenses_data = self.data_from_res(res)
        assert len(licenses_data) == len(register), (len(licenses_data), len(register))
        for license_data in licenses_data:
            id = license_data['id']
            license = register[id]
            assert license['title'] == license.title
            assert license['url'] == license.url


class TestLicensesVersion1(Version1TestCase, LicensesTestCase): pass
class TestLicensesVersion2(Version2TestCase, LicensesTestCase): pass
class TestLicensesUnversioned(UnversionedTestCase, LicensesTestCase): pass
