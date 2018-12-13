# encoding: utf-8

from nose.tools import eq_, ok_, assert_raises

from ckan.exceptions import HelperError
import ckan.plugins as plugins
import ckan.tests.helpers as helpers


class TestFlaskIBlueprint(helpers.FunctionalTestBase):

    def setup(self):
        self.app = helpers._get_test_app()

        # Install plugin and register its blueprint
        if not plugins.plugin_loaded(u'example_flask_iblueprint'):
            plugins.load(u'example_flask_iblueprint')
            plugin = plugins.get_plugin(u'example_flask_iblueprint')
            self.app.flask_app.register_extension_blueprint(plugin.get_blueprint())

    def test_plugin_route(self):
        u'''Test extension sets up a unique route.'''
        res = self.app.get(u'/hello_plugin')

        eq_(u'Hello World, this is served from an extension', res.body)

    def test_plugin_route_core_pylons_override(self):
        u'''Test extension overrides pylons core route.'''
        res = self.app.get(u'/about')

        ok_(u'This is an about page served from an extention, overriding the pylons url.' in res.body)

    def test_plugin_route_core_flask_override(self):
        u'''Test extension overrides flask core route.'''
        res = self.app.get(u'/hello')

        ok_(u'Hello World, this is served from an extension, overriding the flask url.' in res.body)

# TODO This won't work until the url_for work is merged
#    def test_plugin_route_core_flask_override_with_template(self):
#        u'''
#        Test extension overrides a python core route, rendering a core
#        template (home/about.html).
#        '''
#        res = self.app.get(u'/about_core')
#
#        ok_(u'<title>About - CKAN</title>' in res.ubody)

    def test_plugin_route_with_helper(self):
        u'''
        Test extension rendering with a helper method that exists shouldn't
        cause error.
        '''
        res = self.app.get(u'/helper')

        ok_(u'Hello World, helper here: <p><em>hi</em></p>' in res.body)

    def test_plugin_route_with_non_existent_helper(self):
        u'''
        Test extension rendering with a helper method that doesn't exist
        raises an exception.
        '''
        assert_raises(HelperError, self.app.get, u'/helper_not_here')
