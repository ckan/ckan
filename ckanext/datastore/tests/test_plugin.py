import nose

import ckan.plugins as p
import ckanext.datastore.interfaces as interfaces


assert_equal = nose.tools.assert_equal
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
        # This test is complicated because we can't import
        # ckanext.datastore.plugin before running it. If we did so, the
        # DatastorePlugin class would be parsed which breaks the reason of our
        # test.
        p.load('sample_datastore_plugin')
        thrown_exception = None
        try:
            p.load('datastore')
        except Exception as e:
            thrown_exception = e
        idatastores = [x.__class__.__name__ for x
                       in p.PluginImplementations(interfaces.IDatastore)]
        p.unload('sample_datastore_plugin')

        import ckanext.datastore.plugin as datastore
        assert thrown_exception is not None, \
            ('Loading "datastore" after another IDatastore plugin was'
             'loaded should raise DatastoreException')
        assert_equal(thrown_exception.__class__.__name__,
                     datastore.DatastoreException.__name__)
        assert datastore.DatastorePlugin.__name__ not in idatastores, \
            ('You shouldn\'t be able to load the "datastore" plugin after'
             'another IDatastore plugin was loaded')
