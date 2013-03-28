import unittest

import sqlalchemy

import ckanext.datastore.plugin as plugin


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
        self.p.legacy_mode = False
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'
        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u:pass@localhost/ds'

        def handler(message):
            assert 'urls are the same' in message, message
        try:
            self.p._check_urls_and_permissions(handler)
        except sqlalchemy.exc.OperationalError:
            pass
        else:
            assert False

        self.p.ckan_url = 'postgresql://u:pass@localhost/ds'
        self.p.legacy_mode = True

        def handler2(message):
            assert 'cannot be the same' in message, message
        try:
            self.p._check_urls_and_permissions(handler2)
        except sqlalchemy.exc.OperationalError:
            pass
        else:
            assert False

        self.p.read_url = 'postgresql://u2:pass@localhost/ds'
        self.p.legacy_mode = False

        def handler3(message):
            assert 'cannot be the same' in message, message
        try:
            self.p._check_urls_and_permissions(handler3)
        except sqlalchemy.exc.OperationalError:
            pass
        else:
            assert False
