import unittest
from nose.tools import assert_equal

import ckanext.datastore.plugin as plugin

# global variable used for callback tests
msg = ''
called = 0


class TestTypeGetters(unittest.TestCase):
    def setUp(self):
        self.p = plugin.DatastorePlugin()

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

    def test_check_urls_and_permissions(self):
        global msg

        def handler(message):
            global msg, called
            msg = message
            called += 1

        def true_privileges_mock():
            return True

        def false_privileges_mock():
            return False

        self.p.legacy_mode = False
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'
        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u2:pass@localhost/ds'
        self.p._read_connection_has_correct_privileges = true_privileges_mock

        # all urls are correct
        self.p._check_urls_and_permissions(handler)
        assert_equal(msg, '')
        assert_equal(called, 0)

        # same url for read and write but in legacy mode
        self.p.legacy_mode = True
        self.p.read_url = 'postgresql://u:pass@localhost/ds'
        self.p._check_urls_and_permissions(handler)
        assert_equal(msg, '')
        assert_equal(called, 0)

        # same url for read and write
        self.p.legacy_mode = False
        self.p._check_urls_and_permissions(handler)
        assert 'urls are the same' in msg, msg
        assert_equal(called, 1)

        # same ckan and ds db
        self.p.ckan_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u2:pass@localhost/ds'
        self.p._check_urls_and_permissions(handler)
        assert 'cannot be the same' in msg, msg
        assert_equal(called, 2)

        # have write permissions but in legacy mode
        self.p.legacy_mode = True
        msg = ''
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'
        self.p._read_connection_has_correct_privileges = false_privileges_mock
        self.p._check_urls_and_permissions(handler)
        assert_equal(msg, '')
        assert_equal(called, 2)

        # have write permissions
        self.p.legacy_mode = False
        self.p._check_urls_and_permissions(handler)
        assert 'user has write privileges' in msg, msg
        assert_equal(called, 3)

        # everything is wrong
        self.p.ckan_url = 'postgresql://u:pass@localhost/ds'
        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u:pass@localhost/ds'
        self.p._check_urls_and_permissions(handler)
        assert_equal(called, 6)
