# encoding: utf-8

import pytest
import ckan.tests.helpers as helpers
import ckan.plugins.toolkit as toolkit


@pytest.mark.usefixtures("clean_db")
class TestIConfigurerToolkitAddCkanAdminTab(object):

    """
    Tests for toolkit.add_ckan_admin_tab used by the IConfigurer interface.
    """

    def test_add_ckan_admin_tab_updates_config_dict(self):
        """Config dict updated by toolkit.add_ckan_admin_tabs method."""
        config = {}

        toolkit.add_ckan_admin_tab(config, "my_route_name", "my_label")

        assert {
            "ckan.admin_tabs": {
                "my_route_name": {"label": "my_label", "icon": None}
            }
        } == config

    def test_add_ckan_admin_tab_twice(self):
        """
        Calling add_ckan_admin_tab twice with same values returns expected
        config.
        """
        config = {}

        toolkit.add_ckan_admin_tab(config, "my_route_name", "my_label")
        toolkit.add_ckan_admin_tab(config, "my_route_name", "my_label")

        expected_dict = {
            "ckan.admin_tabs": {
                "my_route_name": {"label": "my_label", "icon": None}
            }
        }

        assert expected_dict == config

    def test_add_ckan_admin_tab_twice_replace_value(self):
        """
        Calling add_ckan_admin_tab twice with a different value returns
        expected config.
        """
        config = {}

        toolkit.add_ckan_admin_tab(config, "my_route_name", "my_label")
        toolkit.add_ckan_admin_tab(
            config, "my_route_name", "my_replacement_label"
        )

        expected_dict = {
            "ckan.admin_tabs": {
                "my_route_name": {
                    "label": "my_replacement_label",
                    "icon": None,
                }
            }
        }

        assert expected_dict == config

    def test_add_ckan_admin_tab_two_routes(self):
        """
        Add two different route/label pairs to ckan.admin_tabs.
        """
        config = {}

        toolkit.add_ckan_admin_tab(config, "my_route_name", "my_label")
        toolkit.add_ckan_admin_tab(
            config, "my_other_route_name", "my_other_label"
        )

        expected_dict = {
            "ckan.admin_tabs": {
                "my_other_route_name": {
                    "label": "my_other_label",
                    "icon": None,
                },
                "my_route_name": {"label": "my_label", "icon": None},
            }
        }

        assert expected_dict == config

    def test_add_ckan_admin_tab_config_has_existing_admin_tabs(self):
        """
        Config already has a ckan.admin_tabs option.
        """
        config = {
            "ckan.admin_tabs": {
                "my_existing_route": {
                    "label": "my_existing_label",
                    "icon": None,
                }
            }
        }

        toolkit.add_ckan_admin_tab(config, "my_route_name", "my_label")
        toolkit.add_ckan_admin_tab(
            config, "my_other_route_name", "my_other_label"
        )

        expected_dict = {
            "ckan.admin_tabs": {
                "my_existing_route": {
                    "label": "my_existing_label",
                    "icon": None,
                },
                "my_other_route_name": {
                    "label": "my_other_label",
                    "icon": None,
                },
                "my_route_name": {"label": "my_label", "icon": None},
            }
        }

        assert expected_dict == config

    def test_add_ckan_admin_tab_config_has_existing_other_option(self):
        """
        Config already has existing other option.
        """
        config = {"ckan.my_option": "This is my option"}

        toolkit.add_ckan_admin_tab(config, "my_route_name", "my_label")
        toolkit.add_ckan_admin_tab(
            config, "my_other_route_name", "my_other_label"
        )

        expected_dict = {
            "ckan.my_option": "This is my option",
            "ckan.admin_tabs": {
                "my_other_route_name": {
                    "label": "my_other_label",
                    "icon": None,
                },
                "my_route_name": {"label": "my_label", "icon": None},
            },
        }

        assert expected_dict == config
