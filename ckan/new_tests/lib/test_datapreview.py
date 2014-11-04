# -*- coding: utf-8 -*-
import nose

import ckan.plugins as p
import ckan.lib.datapreview as datapreview

from ckan.new_tests import helpers, factories


eq_ = nose.tools.eq_


class TestDataPreview(object):

    def test_compare_domains(self):
        ''' see https://en.wikipedia.org/wiki/Same_origin_policy
        '''
        compare = datapreview.compare_domains
        eq_(compare(['http://www.okfn.org', 'http://www.okfn.org']), True)
        eq_(compare(['http://www.okfn.org', 'http://www.okfn.org',
                     'http://www.okfn.org']), True)
        eq_(compare(['http://www.OKFN.org', 'http://www.okfn.org',
                     'http://www.okfn.org/test/foo.html']), True)
        eq_(compare(['http://okfn.org', 'http://okfn.org']), True)
        eq_(compare(['www.okfn.org', 'http://www.okfn.org']), True)
        eq_(compare(['//www.okfn.org', 'http://www.okfn.org']), True)
        eq_(compare(['http://www.okfn.org', 'https://www.okfn.org']), False)
        eq_(compare(['http://www.okfn.org:80',
                     'http://www.okfn.org:81']), False)
        eq_(compare(['http://www.okfn.org', 'http://www.okfn.de']), False)
        eq_(compare(['http://de.okfn.org', 'http://www.okfn.org']), False)
        eq_(compare(['http://de.okfn.org', 'http:www.foo.com']), False)
        eq_(compare(['httpö://wöwöwö.ckan.dö', 'www.ckän.örg']), False)
        eq_(compare(['www.ckän.örg', 'www.ckän.örg']), True)
        eq_(compare(['http://Server=cda3; Service=sde:sqlserver:cda3; ',
                     'http://www.okf.org']), False)


class MockDatastoreBasedResourceView(p.SingletonPlugin):

    p.implements(p.IResourceView)

    def info(self):
        return {
            'name': 'test_datastore_view',
            'title': 'Test Datastore View',
            'requires_datastore': True,
        }


class TestDefaultViewsConfig(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')
        if not p.plugin_loaded('webpage_view'):
            p.load('webpage_view')
        if not p.plugin_loaded('test_datastore_view'):
            p.load('test_datastore_view')

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')
        p.unload('webpage_view')
        p.unload('test_datastore_view')

    def test_no_config(self):

        default_views = datapreview.get_default_view_plugins()

        eq_(sorted([view_plugin.info()['name'] for view_plugin in default_views]),
            sorted(datapreview.DEFAULT_RESOURCE_VIEW_TYPES))

    @helpers.change_config('ckan.views.default_views', '')
    def test_empty_config(self):

        default_views = datapreview.get_default_view_plugins()

        eq_(default_views, [])

    @helpers.change_config('ckan.views.default_views', 'image')
    def test_in_config(self):

        default_views = datapreview.get_default_view_plugins()

        eq_(sorted([view_plugin.info()['name'] for view_plugin in default_views]),
            ['image'])

    @helpers.change_config('ckan.views.default_views', 'test_datastore_view')
    def test_in_config_datastore_view_only(self):

        default_views = datapreview.get_default_view_plugins(get_datastore_views=True)

        eq_(sorted([view_plugin.info()['name'] for view_plugin in default_views]),
            ['test_datastore_view'])

    @helpers.change_config('ckan.views.default_views', 'test_datastore_view')
    def test_in_config_datastore_view_only_with_get_datastore_views(self):

        default_views = datapreview.get_default_view_plugins()

        eq_(default_views, [])

    @helpers.change_config('ckan.views.default_views', 'image test_datastore_view')
    def test_both_plugins_in_config_only_non_datastore(self):

        default_views = datapreview.get_default_view_plugins()

        eq_(sorted([view_plugin.info()['name'] for view_plugin in default_views]),
            ['image'])

    @helpers.change_config('ckan.views.default_views', 'image test_datastore_view')
    def test_both_plugins_in_config_only_datastore(self):

        default_views = datapreview.get_default_view_plugins(get_datastore_views=True)

        eq_(sorted([view_plugin.info()['name'] for view_plugin in default_views]),
            ['test_datastore_view'])
