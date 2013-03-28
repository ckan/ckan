import unittest

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

    def test_check_separate_write_and_read_if_not_legacy(self):
        self.p.legacy_mode = True
        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u:pass@localhost/ds'
        assert not self.p._same_read_and_write_url()

        self.p.legacy_mode = False

        assert not self.p.legacy_mode

        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u:pass@localhost/ds'
        assert self.p._same_read_and_write_url()

        self.p.write_url = 'postgresql://u:pass@localhost/ds'
        self.p.read_url = 'postgresql://u2:pass@localhost/ds'
        assert not self.p._same_read_and_write_url()

    def test_same_ckan_and_datastore_db(self):
        self.p.write_url = 'postgresql://u:pass@localhost/ckan'
        self.p.read_url = 'postgresql://u:pass@localhost/ckan'
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'

        assert self.p._same_ckan_and_datastore_db()

        self.p.write_url = 'postgresql://u:pass@localhost/dt'
        self.p.read_url = 'postgresql://u:pass@localhost/dt'
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'

        assert not self.p._same_ckan_and_datastore_db()
