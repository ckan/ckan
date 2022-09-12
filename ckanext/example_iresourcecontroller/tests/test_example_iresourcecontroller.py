# encoding: utf-8

"""Tests for the ckanext.example_iauthfunctions extension.

"""
import pytest

import ckan.plugins
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config("ckan.plugins", "example_iresourcecontroller")
@pytest.mark.usefixtures("non_clean_db", "with_plugins", "with_request_context")
class TestExampleIResourceController(object):
    """Tests for the plugin that uses IResourceController.

    """

    def test_resource_controller_plugin_create(self):
        user = factories.Sysadmin()
        package = factories.Dataset(user=user)

        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_create",
            package_id=package["id"],
            name="test-resource",
            url="http://resource.create/",
            apikey=user["apikey"],
        )

        assert plugin.counter["before_resource_create"] == 1, plugin.counter
        assert plugin.counter["after_resource_create"] == 1, plugin.counter
        assert plugin.counter["before_resource_update"] == 0, plugin.counter
        assert plugin.counter["after_resource_update"] == 0, plugin.counter
        assert plugin.counter["before_resource_delete"] == 0, plugin.counter
        assert plugin.counter["after_resource_delete"] == 0, plugin.counter

    def test_resource_controller_plugin_update(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)
        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://resource.updated/",
            apikey=user["apikey"],
        )

        assert plugin.counter["before_resource_create"] == 1, plugin.counter
        assert plugin.counter["after_resource_create"] == 1, plugin.counter
        assert plugin.counter["before_resource_update"] == 1, plugin.counter
        assert plugin.counter["after_resource_update"] == 1, plugin.counter
        assert plugin.counter["before_resource_delete"] == 0, plugin.counter
        assert plugin.counter["after_resource_delete"] == 0, plugin.counter

    def test_resource_controller_plugin_delete(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)

        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_delete", id=resource["id"], apikey=user["apikey"]
        )

        assert plugin.counter["before_resource_create"] == 1, plugin.counter
        assert plugin.counter["after_resource_create"] == 1, plugin.counter
        assert plugin.counter["before_resource_update"] == 0, plugin.counter
        assert plugin.counter["after_resource_update"] == 0, plugin.counter
        assert plugin.counter["before_resource_delete"] == 1, plugin.counter
        assert plugin.counter["after_resource_delete"] == 1, plugin.counter

    def test_resource_controller_plugin_show(self):
        """
        Before show gets called by the other methods but we test it
        separately here and make sure that it doesn't call the other
        methods.
        """
        user = factories.Sysadmin()
        package = factories.Dataset(user=user)
        factories.Resource(user=user, package_id=package["id"])

        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action("package_show", name_or_id=package["id"])

        assert plugin.counter["before_resource_create"] == 1, plugin.counter
        assert plugin.counter["after_resource_create"] == 1, plugin.counter
        assert plugin.counter["before_resource_update"] == 0, plugin.counter
        assert plugin.counter["after_resource_update"] == 0, plugin.counter
        assert plugin.counter["before_resource_delete"] == 0, plugin.counter
        assert plugin.counter["after_resource_delete"] == 0, plugin.counter
        assert plugin.counter["before_resource_show"] == 4, plugin.counter
