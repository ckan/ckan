import unittest
import nose.tools
import pyutilib.component.core

import ckan.plugins
#import ckanext.datastore.plugin as plugin


class _TestConfiguration(unittest.TestCase):
    # FIXME This entire test class is broken and currently disabled.  A test
    # should not be changing the plugin itself WTF!  I'm not sure if these
    # tests have any value whatsoever.  Anyhow the plugin is not capable of
    # being so tested.  Also why do these test raise a custom exception?
    def setUp(self):
        self._original_plugin = ckan.plugins.unload('datastore')
        pyutilib.component.core.PluginGlobals.singleton_services()[plugin.DatastorePlugin] = True
        self.p = pyutilib.component.core.PluginGlobals.singleton_services()[plugin.DatastorePlugin] = ckan.plugins.load('datastore')

    def tearDown(self):
        ckan.plugins.unload('datastore')
        pyutilib.component.core.PluginGlobals.singleton_services()[plugin.DatastorePlugin] = self._original_plugin

    def test_set_legacy_mode(self):
        c = {
            'sqlalchemy.url': 'bar',
            'ckan.datastore.write_url': 'foo'
        }
        try:
            self.p.configure(c)
        except Exception:
            pass
        assert self.p.legacy_mode
        assert self.p.write_url == 'foo'
        assert self.p.read_url == 'foo'

    def test_check_separate_write_and_read_url(self):
        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u:pass@localhost/ds'
        assert self.p._same_read_and_write_url()

        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u2:pass@localhost/ds'
        assert not self.p._same_read_and_write_url()

    def test_same_ckan_and_datastore_db(self):
        self.p.read_url = 'postgresql://u2:pass@localhost/ckan'
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'
        assert self.p._same_ckan_and_datastore_db()

        self.p.read_url = 'postgresql://u:pass@localhost/dt'
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'
        assert not self.p._same_ckan_and_datastore_db()

    def test_setup_plugin_for_check_urls_and_permissions_tests_should_leave_the_plugin_in_a_valid_state(self):
        self.setUp_plugin_for_check_urls_and_permissions_tests()
        self.p._check_urls_and_permissions()  # Should be OK

    def test_check_urls_and_permissions_requires_different_ckan_and_datastore_dbs(self):
        self.setUp_plugin_for_check_urls_and_permissions_tests()

        self.p._same_ckan_and_datastore_db = lambda: False
        self.p._check_urls_and_permissions()  # Should be OK

        self.p._same_ckan_and_datastore_db = lambda: True
        nose.tools.assert_raises(InvalidUrlsOrPermissionsException, self.p._check_urls_and_permissions)

    def test_check_urls_and_permissions_requires_different_read_and_write_urls_when_not_in_legacy_mode(self):
        self.setUp_plugin_for_check_urls_and_permissions_tests()
        self.p.legacy_mode = False

        self.p._same_read_and_write_url = lambda: False
        self.p._check_urls_and_permissions()  # Should be OK

        self.p._same_read_and_write_url = lambda: True
        nose.tools.assert_raises(InvalidUrlsOrPermissionsException, self.p._check_urls_and_permissions)

    def test_check_urls_and_permissions_doesnt_require_different_read_and_write_urls_when_in_legacy_mode(self):
        self.setUp_plugin_for_check_urls_and_permissions_tests()
        self.p.legacy_mode = True

        self.p._same_read_and_write_url = lambda: False
        self.p._check_urls_and_permissions()  # Should be OK

        self.p._same_read_and_write_url = lambda: True
        self.p._check_urls_and_permissions()  # Should be OK

    def test_check_urls_and_permissions_requires_read_connection_with_correct_privileges_when_not_in_legacy_mode(self):
        self.setUp_plugin_for_check_urls_and_permissions_tests()
        self.p.legacy_mode = False

        self.p._read_connection_has_correct_privileges = lambda: True
        self.p._check_urls_and_permissions()  # Should be OK

        self.p._read_connection_has_correct_privileges = lambda: False
        nose.tools.assert_raises(InvalidUrlsOrPermissionsException, self.p._check_urls_and_permissions)

    def test_check_urls_and_permissions_doesnt_care_about_read_connection_privileges_when_in_legacy_mode(self):
        self.setUp_plugin_for_check_urls_and_permissions_tests()
        self.p.legacy_mode = True

        self.p._read_connection_has_correct_privileges = lambda: True
        self.p._check_urls_and_permissions()  # Should be OK

        self.p._read_connection_has_correct_privileges = lambda: False
        self.p._check_urls_and_permissions()  # Should be OK

    def setUp_plugin_for_check_urls_and_permissions_tests(self):
        def _raise_invalid_urls_or_permissions_exception(message):
            raise InvalidUrlsOrPermissionsException(message)

        self.p._same_ckan_and_datastore_db = lambda: False
        self.p.legacy_mode = True
        self.p._same_read_and_write_url = lambda: False
        self.p._read_connection_has_correct_privileges = lambda: True
        self.p._log_or_raise = _raise_invalid_urls_or_permissions_exception


class InvalidUrlsOrPermissionsException(Exception):
    pass
