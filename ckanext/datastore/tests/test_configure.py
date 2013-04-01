import unittest
import ckan.plugins as p
from nose.tools import raises

import ckanext.datastore.plugin as plugin


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.p = p.load('datastore')

    def tearDown(self):
        p.unload('datastore')

    def test_legacy_mode_default(self):
        assert not self.p.legacy_mode

    def test_set_legacy_mode(self):
        assert not self.p.legacy_mode
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


class TestCheckUrlsAndPermissions(unittest.TestCase):
    def setUp(self):
        self.p = p.load('datastore')

        self.p.legacy_mode = False

        # initialize URLs
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'
        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u2:pass@localhost/ds'

        # initialize mock for privileges check
        def true_privileges_mock():
            return True
        self.p._read_connection_has_correct_privileges = true_privileges_mock

        def raise_datastore_exception(message):
            raise plugin.DatastoreException(message)
        self.p._log_or_raise = raise_datastore_exception

    def tearDown(self):
        p.unload('datastore')

    def test_everything_correct_does_not_raise(self):
        self.p._check_urls_and_permissions()

    @raises(plugin.DatastoreException)
    def test_raises_when_ckan_and_datastore_db_are_the_same(self):
        self.p.read_url = 'postgresql://u2:pass@localhost/ckan'
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'

        self.p._check_urls_and_permissions()

    @raises(plugin.DatastoreException)
    def test_raises_when_same_read_and_write_url(self):
        self.p.read_url = 'postgresql://u:pass@localhost/ds'
        self.p.write_url = 'postgresql://u:pass@localhost/ds'

        self.p._check_urls_and_permissions()

    def test_same_read_and_write_url_in_legacy_mode(self):
        self.p.read_url = 'postgresql://u:pass@localhost/ds'
        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.legacy_mode = True

        self.p._check_urls_and_permissions()

    @raises(plugin.DatastoreException)
    def test_raises_when_we_have_write_permissions(self):
        def false_privileges_mock():
            return False
        self.p._read_connection_has_correct_privileges = false_privileges_mock
        self.p._check_urls_and_permissions()

    def test_have_write_permissions_in_legacy_mode(self):
        def false_privileges_mock():
            return False
        self.p._read_connection_has_correct_privileges = false_privileges_mock
        self.p.legacy_mode = True

        self.p._check_urls_and_permissions()
