# -*- coding: utf-8 -*-

from ckan import plugins

class TestChainedFunctionsPlugin(object):

    @classmethod
    def setup_class(self):
        if not plugins.plugin_loaded('chained_functions'):
            plugins.load('chained_functions')

    @classmethod
    def teardown_class(self):
        if plugins.plugin_loaded('chained_functions'):
            plugins.unload('chained_functions')

    def test_auth_attributes_are_retained(self):
        from ckan.authz import _AuthFunctions
        user_show = _AuthFunctions.get("user_show")
        assert hasattr(user_show, 'auth_allow_anonymous_access') is True

    def test_action_attributes_are_retained(self):
        from ckan.plugins.toolkit import get_action
        package_search = get_action('package_search')
        assert hasattr(package_search, 'side_effect_free') is True
