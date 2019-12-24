# encoding: utf-8

import pytest

from ckan.exceptions import HelperError
import ckan.plugins as plugins
import ckan.tests.helpers as helpers


class TestFlaskIBlueprint(helpers.FunctionalTestBase):
    def setup(self):
        self.app = helpers._get_test_app()

        # Install plugin and register its blueprint
        if not plugins.plugin_loaded(u"example_flask_iblueprint"):
            plugins.load(u"example_flask_iblueprint")
            plugin = plugins.get_plugin(u"example_flask_iblueprint")
            self.app.flask_app.register_extension_blueprint(
                plugin.get_blueprint()
            )

    def test_plugin_route(self):
        u"""Test extension sets up a unique route."""
        res = self.app.get(u"/hello_plugin")

        assert u"Hello World, this is served from an extension" == res.body

    def test_plugin_route_core_flask_override(self):
        u"""Test extension overrides flask core route."""
        res = self.app.get(u"/")

        assert helpers.body_contains(
            res,
            u"Hello World, this is served from an extension, "
            u"overriding the flask url."
        )

    def test_plugin_route_with_helper(self):
        u"""
        Test extension rendering with a helper method that exists shouldn't
        cause error.
        """
        res = self.app.get(u"/helper")

        assert helpers.body_contains(res, u"Hello World, helper here: <p><em>hi</em></p>")

    def test_plugin_route_with_non_existent_helper(self):
        u"""
        Test extension rendering with a helper method that doesn't exist
        raises an exception.
        """
        with pytest.raises(HelperError):
            self.app.get(u"/helper_not_here")
