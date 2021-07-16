# encoding: utf-8

import pytest

from ckan.exceptions import HelperError
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config("ckan.plugins", "example_flask_iblueprint")
@pytest.mark.usefixtures("clean_db", "with_plugins")
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
        res = app.get("/helper")

        assert helpers.body_contains(res, "Hello World, helper here: <p><em>hi</em></p>")

    def test_plugin_route_with_non_existent_helper(self, app):
        """
        Test extension rendering with a helper method that doesn't exist
        raises an exception.
        """
        with pytest.raises(HelperError):
            app.get("/helper_not_here")

    def test_flask_request_in_template(self, app):
        """
        Test that we are using Flask request wrapped with CKANRequest
        params is should be accessible for backward compatibility
        """
        res = app.get("/flask_request?test=it_works")
        assert helpers.body_contains(res, 'it_works')
