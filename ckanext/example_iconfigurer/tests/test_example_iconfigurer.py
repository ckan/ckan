# encoding: utf-8
import pytest

import ckan.tests.helpers as helpers


@pytest.mark.ckan_config("ckan.plugins", u"example_iconfigurer")
@pytest.mark.usefixtures("with_plugins")
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
