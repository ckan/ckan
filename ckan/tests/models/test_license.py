from ckan.model.license import LicenseRegister

class TestLicense:

    def setup(self):
        self.licenses = LicenseRegister()

    def teardown(self):
        self.licenses = None

    def test_keys(self):
        for license_id in self.licenses.keys():
            assert type(license_id) == str
    
    def test_values(self):
        for license in self.licenses.values():
            assert type(license['id']) == str
    
    def test_iter(self):
        for license_id in self.licenses:
            print "License ID: %s" % license_id
            assert type(license_id) == str, license_id
    
    def test_getitem(self):
        for license_id in self.licenses.keys():
            assert type(self.licenses[license_id]['title']) == str

