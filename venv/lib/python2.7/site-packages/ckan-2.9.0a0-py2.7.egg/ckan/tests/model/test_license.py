# encoding: utf-8

import os

from nose.tools import assert_equal
from ckan.common import config

from ckan.model.license import LicenseRegister
from ckan.tests import helpers


class TestLicenseRegister(object):

    def setup(self):
        helpers.reset_db()

    def test_default_register_has_basic_properties_of_a_license(self):
        config['licenses_group_url'] = None
        reg = LicenseRegister()

        license = reg['cc-by']
        assert_equal(license.url,
                     'http://www.opendefinition.org/licenses/cc-by')
        assert_equal(license.isopen(), True)
        assert_equal(license.title, 'Creative Commons Attribution')

    def test_import_v1_style_register(self):
        this_dir = os.path.dirname(os.path.realpath(__file__))
        # v1 is used by CKAN so far
        register_filepath = '%s/licenses.v1' % this_dir
        config['licenses_group_url'] = 'file:///%s' % register_filepath
        reg = LicenseRegister()

        license = reg['cc-by']
        assert_equal(license.url,
                     'http://www.opendefinition.org/licenses/cc-by')
        assert_equal(license.isopen(), True)
        assert_equal(license.title, 'Creative Commons Attribution')

    def test_import_v2_style_register(self):
        this_dir = os.path.dirname(os.path.realpath(__file__))
        # v2 is used by http://licenses.opendefinition.org in recent times
        register_filepath = '%s/licenses.v2' % this_dir
        config['licenses_group_url'] = 'file:///%s' % register_filepath
        reg = LicenseRegister()

        license = reg['CC-BY-4.0']
        assert_equal(license.url,
                     'https://creativecommons.org/licenses/by/4.0/')
        assert_equal(license.isopen(), True)
        assert_equal(license.title, 'Creative Commons Attribution 4.0')


class TestLicense:
    def test_access_via_attribute(self):
        license = LicenseRegister()['cc-by']
        assert_equal(license.od_conformance, 'approved')

    def test_access_via_key(self):
        license = LicenseRegister()['cc-by']
        assert_equal(license['od_conformance'], 'approved')

    def test_access_via_dict(self):
        license = LicenseRegister()['cc-by']
        license_dict = license.as_dict()
        assert_equal(license_dict['od_conformance'], 'approved')
        assert_equal(license_dict['osd_conformance'], 'not reviewed')


class TestLicenseLegacyFields:
    def test_access_via_attribute(self):
        license = LicenseRegister()['cc-by']
        assert_equal(license.is_okd_compliant, True)
        assert_equal(license.is_osi_compliant, False)

    def test_access_via_key(self):
        license = LicenseRegister()['cc-by']
        assert_equal(license['is_okd_compliant'], True)
        assert_equal(license['is_osi_compliant'], False)

    def test_access_via_dict(self):
        license = LicenseRegister()['cc-by']
        license_dict = license.as_dict()
        assert_equal(license_dict['is_okd_compliant'], True)
        assert_equal(license_dict['is_osi_compliant'], False)
