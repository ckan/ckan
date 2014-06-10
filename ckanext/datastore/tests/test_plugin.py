import nose

import ckan.plugins as p
import ckanext.datastore.plugin as datastore


assert_raises = nose.tools.assert_raises


class TestPlugin(object):
    @classmethod
    def setup(cls):
        if p.plugin_loaded('datastore'):
            p.unload('datastore')
        if p.plugin_loaded('sample_datastore_plugin'):
            p.unload('sample_datastore_plugin')

    def test_loading_datastore_first_works(self):
        p.load('datastore')
        p.load('sample_datastore_plugin')
        p.unload('sample_datastore_plugin')
        p.unload('datastore')

    def test_loading_datastore_last_doesnt_work(self):
        p.load('sample_datastore_plugin')
        assert_raises(datastore.DatastoreException, p.load, 'datastore')
        p.unload('sample_datastore_plugin')
