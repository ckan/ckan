from nose.tools import eq_, ok_

import ckan.plugins as plugins
import ckan.tests.helpers as helpers


class TestFlaskIBlueprint(helpers.FunctionalTestBase):

    def setup(self):
        self.app = helpers._get_test_app()
        flask_app = helpers.find_flask_app(self.app)

        # Install plugin and register its blueprint
        if not plugins.plugin_loaded('example_flask_iblueprint'):
            plugins.load('example_flask_iblueprint')
            plugin = plugins.get_plugin('example_flask_iblueprint')
            flask_app.register_blueprint(plugin.get_blueprint(),
                                         prioritise_rules=True)

    def test_plugin_route(self):
        '''Test extension sets up a unique route.'''
        res = self.app.get('/hello_plugin')

        eq_('Hello World, this is served from an extension', res.body)

    def test_plugin_route_core_pylons_override(self):
        '''Test extension overrides pylons core route.'''
        res = self.app.get('/about')

        ok_('This is an about page served from an extention, overriding the pylons url.' in res.body)

    def test_plugin_route_core_flask_override(self):
        '''Test extension overrides flask core route.'''
        res = self.app.get('/hello')

        ok_('Hello World, this is served from an extension, overriding the flask url.' in res.body)

    def test_plugin_route_with_helper(self):
        '''
        Test extension rendering with a helper method that exists shouldn't
        cause error.
        '''
        res = self.app.get('/helper')

        ok_('Hello World, helper here: en' in res.body)

    def test_plugin_route_with_non_existent_helper(self):
        '''
        Test extension rendering with a helper method that doesn't exist
        causes server error.
        '''
        self.app.get('/helper_not_here', status=500)
