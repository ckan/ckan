# encoding: utf-8

import unittest

import ckan.plugins
import nose.tools
import pyutilib.component.core


# import ckanext.datastore.plugin as plugin


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

    def test_check_urls_and_permissions_requires_different_read_and_write_urls(self):
        self.setUp_plugin_for_check_urls_and_permissions_tests()

        self.p._same_read_and_write_url = lambda: False
        self.p._check_urls_and_permissions()  # Should be OK

        self.p._same_read_and_write_url = lambda: True
        nose.tools.assert_raises(InvalidUrlsOrPermissionsException, self.p._check_urls_and_permissions)

    def test_check_urls_and_permissions_requires_read_connection_with_correct_privileges(self):
        self.setUp_plugin_for_check_urls_and_permissions_tests()

        self.p._read_connection_has_correct_privileges = lambda: True
        self.p._check_urls_and_permissions()  # Should be OK

        self.p._read_connection_has_correct_privileges = lambda: False
        nose.tools.assert_raises(InvalidUrlsOrPermissionsException, self.p._check_urls_and_permissions)


class InvalidUrlsOrPermissionsException(Exception):
    pass
