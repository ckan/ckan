# encoding: utf-8

import pytest

from ckan.exceptions import HelperError
import ckan.plugins as plugins
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_iblueprint")
@pytest.mark.usefixtures(u"clean_db", u"with_plugins")
class TestFlaskIBlueprint(object):

    def test_plugin_route(self, app):
        u"""Test extension sets up a unique route."""
        res = app.get(u"/hello_plugin")

        assert helpers.body_contains(res, u"Hello World, this is served from an extension")

    def test_plugin_route_core_flask_override(self, app):
        u"""Test extension overrides flask core route."""
        res = app.get(u"/")

        assert helpers.body_contains(
            res,
            u"Hello World, this is served from an extension, "
            u"overriding the flask url."
        )

    def test_plugin_route_with_helper(self, app):
        u"""
        Test extension rendering with a helper method that exists shouldn't
        cause error.
        """
        res = app.get(u"/helper")

        assert helpers.body_contains(res, u"Hello World, helper here: <p><em>hi</em></p>")

    def test_plugin_route_with_non_existent_helper(self, app):
        u"""
        Test extension rendering with a helper method that doesn't exist
        raises an exception.
        """
        with pytest.raises(HelperError):
            app.get(u"/helper_not_here")
