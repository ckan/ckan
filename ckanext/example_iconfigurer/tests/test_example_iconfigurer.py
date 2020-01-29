# encoding: utf-8

import six
import pytest

import ckan.tests.helpers as helpers
import ckan.plugins as plugins


@pytest.mark.ckan_config("ckan.plugins", u"example_iconfigurer")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestExampleIConfigurer(object):
    def test_template_renders(self, app):
        """Our controller renders the extension's config template."""
        response = app.get("/ckan-admin/myext_config_one")
        assert response.status_code == 200
        assert helpers.body_contains(response, "My First Config Page")

    def test_config_page_has_custom_tabs(self, app):
        """
        The admin base template should include our custom ckan-admin tabs
        added using the toolkit.add_ckan_admin_tab method.
        """
        response = app.get("/ckan-admin/myext_config_one", status=200)
        assert response.status_code == 200
        # The label text
        assert helpers.body_contains(response, "My First Custom Config Tab")
        assert helpers.body_contains(response, "My Second Custom Config Tab")
        # The link path
        assert helpers.body_contains(response, "/ckan-admin/myext_config_one")
        assert helpers.body_contains(response, "/ckan-admin/myext_config_two")


@pytest.mark.ckan_config("ckan.plugins", u"example_iconfigurer")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestExampleIConfigurerBuildExtraAdminTabsHelper(object):
    """Tests for helpers.build_extra_admin_nav method."""

    def test_build_extra_admin_nav_config_option_present_but_empty(
        self, app, ckan_config, monkeypatch
    ):
        """
        Empty string returned when ckan.admin_tabs option in config but empty.
        """
        monkeypatch.setitem(ckan_config, "ckan.admin_tabs", {})
        expected = ""
        response = app.get("/build_extra_admin_nav")
        assert six.ensure_text(response.data) == expected

    def test_build_extra_admin_nav_one_value_in_config(
        self, app, ckan_config, monkeypatch
    ):
        """
        Correct string returned when ckan.admin_tabs option has single value in config.
        """
        monkeypatch.setitem(
            ckan_config,
            "ckan.admin_tabs",
            {
                "example_iconfigurer.config_one": {
                    "label": "My Label",
                    "icon": None,
                }
            },
        )
        expected = (
            """<li><a href="/ckan-admin/myext_config_one">My Label</a></li>"""
        )

        response = app.get("/build_extra_admin_nav")
        assert six.ensure_text(response.data) == expected

    def test_build_extra_admin_nav_two_values_in_config(
        self, app, ckan_config, monkeypatch
    ):
        """
        Correct string returned when ckan.admin_tabs option has two values in config.
        """
        monkeypatch.setitem(
            ckan_config,
            "ckan.admin_tabs",
            {
                "example_iconfigurer.config_one": {
                    "label": "My Label",
                    "icon": "picture-o",
                },
                "example_iconfigurer.config_two": {
                    "label": "My Other Label",
                    "icon": None,
                },
            },
        )
        expected = """<li><a href="/ckan-admin/myext_config_one"><i class="fa fa-picture-o"></i> My Label</a></li><li><a href="/ckan-admin/myext_config_two">My Other Label</a></li>"""
        response = app.get("/build_extra_admin_nav")
        assert six.ensure_text(response.data) == expected
