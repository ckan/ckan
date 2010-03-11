from ckan.model.license import LicenseRegister
import datetime

class TestCase(object):

    def assert_unicode(self, val):
        assert isinstance(val, unicode), "Value is not a unicode value: %s" % repr(val)

    def assert_datetime(self, val):
        assert isinstance(val, datetime.datetime), "Value is not a datetime value: %s" % repr(val)


class TestLicense(TestCase):

    def setup(self):
        self.licenses = LicenseRegister()

    def teardown(self):
        self.licenses = None

    def test_keys(self):
        for license_id in self.licenses.keys():
            self.assert_unicode(license_id)
    
    def test_values(self):
        for license in self.licenses.values():
            self.assert_unicode(license.id)
    
    def test_iter(self):
        for license_id in self.licenses:
            self.assert_unicode(license_id)
    
    def test_getitem(self):
        for license_id in self.licenses.keys():
            license = self.licenses[license_id]
            self.assert_unicode(license.id)
            self.assert_unicode(license.title)
            self.assert_datetime(license.date_created)
            self.assert_unicode(license.url)

