# encoding: utf-8

import pytest

from ckan.exceptions import HelperError
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config("ckan.plugins", "example_flask_iblueprint")
@pytest.mark.usefixtures("with_plugins")
class TestFlaskIBlueprint(object):

    def test_plugin_route(self, app):
        """Test extension sets up a unique route."""
        res = app.get("/hello_plugin")

        assert helpers.body_contains(res, "Hello World, this is served from an extension")

    def test_plugin_route_core_flask_override(self, app):
        """Test extension overrides flask core route."""
        res = app.get("/")

        assert helpers.body_contains(
            res,
            "Hello World, this is served from an extension, "
            "overriding the flask url."
        )

    def test_plugin_route_with_helper(self, app):
        """
        Test extension rendering with a helper method that exists shouldn't
        cause error.
        """
        res = app.get(u"/helper")

        assert helpers.body_contains(res, "Hello World, helper here: <p><em>hi</em></p>")

    def test_plugin_route_with_non_existent_helper(self, app):
        """
        Test extension rendering with a helper method that doesn't exist
        raises an exception.
        """
        with pytest.raises(HelperError):
            app.get("/helper_not_here")

    def test_plugin_route_in_second_blueprint(self, app):
        """
        Test extension registers routes in all the blueprints.
        """
        res = app.get("/another_blueprint")
        assert helpers.body_contains(res, "the second blueprint")
