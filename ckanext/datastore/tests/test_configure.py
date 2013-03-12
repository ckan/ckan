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

    def test_check_separate_db(self):
        self.p.write_url = 'postgresql://u:pass@localhost/dt'
        self.p.read_url = 'postgresql://u:pass@localhost/dt'
        self.p.ckan_url = 'postgresql://u:pass@localhost/ckan'

        self.p.legacy_mode = True
        try:
            self.p._check_separate_db()
        except Exception:
            self.fail("_check_separate_db raise Exception unexpectedly!")

        self.p.legacy_mode = False
        self.assertRaises(Exception, self.p._check_separate_db)
