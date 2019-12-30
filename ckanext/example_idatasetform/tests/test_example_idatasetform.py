# encoding: utf-8

import pytest
import six
from ckan.common import config

from ckan.lib.helpers import url_for

import ckan.model as model
import ckan.plugins as plugins
import ckan.tests.helpers as helpers
import ckanext.example_idatasetform as idf
import ckan.lib.search


@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
class ExampleIDatasetFormPluginBase(object):
    """Version 1, 2 and 3 of the plugin are basically the same, so this class
    provides the tests that all three versions of the plugins will run"""

    def test_package_create(self):
        result = helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
        )
        assert "this is my custom text" == result["custom_text"]

    def test_package_update(self):
        helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
        )
        result = helpers.call_action(
            "package_update",
            name="test_package",
            custom_text="this is my updated text",
        )
        assert "this is my updated text" == result["custom_text"]

    def test_package_show(self):
        helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
        )
        result = helpers.call_action("package_show", name_or_id="test_package")
        assert "this is my custom text" == result["custom_text"]


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v1")
class TestVersion1(ExampleIDatasetFormPluginBase):
    pass


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v2")
class TestVersion2(ExampleIDatasetFormPluginBase):
    pass


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v3")
class TestVersion3(ExampleIDatasetFormPluginBase):
    pass


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v5")
@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
class TestVersion5(object):
    def test_custom_package_type_urls(self, test_request_context):
        with test_request_context():
            assert url_for("fancy_type.search") == "/fancy_type/"
            assert url_for("fancy_type.new") == "/fancy_type/new"
            assert (
                url_for("fancy_type.read", id="check") == "/fancy_type/check"
            )
            assert (
                url_for("fancy_type.edit", id="check")
                == "/fancy_type/edit/check"
            )


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v4")
@pytest.mark.usefixtures(
    "clean_db", "clean_index", "with_plugins", "with_request_context"
)
class TestIDatasetFormPluginVersion4(object):
    def test_package_create(self, test_request_context):
        with test_request_context():
            idf.plugin_v4.create_country_codes()
        result = helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
            country_code="uk",
        )
        assert "this is my custom text" == result["custom_text"]
        assert [u"uk"] == result["country_code"]

    def test_package_create_wrong_country_code(self, test_request_context):
        with test_request_context():
            idf.plugin_v4.create_country_codes()
        with pytest.raises(plugins.toolkit.ValidationError):
            helpers.call_action(
                "package_create",
                name="test_package",
                custom_text="this is my custom text",
                country_code="notcode",
            )

    def test_package_update(self, test_request_context):
        with test_request_context():
            idf.plugin_v4.create_country_codes()
        helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
            country_code="uk",
        )
        result = helpers.call_action(
            "package_update",
            name="test_package",
            custom_text="this is my updated text",
            country_code="ie",
        )
        assert "this is my updated text" == result["custom_text"]
        assert [u"ie"] == result["country_code"]


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform")
@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
class TestIDatasetFormPlugin(object):
    def test_package_create(self, test_request_context):
        with test_request_context():
            idf.plugin.create_country_codes()
        result = helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
            country_code="uk",
            resources=[
                {
                    "url": "http://test.com/",
                    "custom_resource_text": "my custom resource",
                }
            ],
        )
        assert (
            "my custom resource"
            == result["resources"][0]["custom_resource_text"]
        )

    def test_package_update(self, test_request_context):
        with test_request_context():
            idf.plugin.create_country_codes()
        helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
            country_code="uk",
            resources=[
                {
                    "url": "http://test.com/",
                    "custom_resource_text": "my custom resource",
                }
            ],
        )
        result = helpers.call_action(
            "package_update",
            name="test_package",
            custom_text="this is my updated text",
            country_code="ie",
            resources=[
                {
                    "url": "http://test.com/",
                    "custom_resource_text": "updated custom resource",
                }
            ],
        )
        assert "this is my updated text" == result["custom_text"]
        assert [u"ie"] == result["country_code"]
        assert (
            "updated custom resource"
            == result["resources"][0]["custom_resource_text"]
        )

    def test_package_show(self, test_request_context):
        with test_request_context():
            idf.plugin.create_country_codes()
        helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
            country_code="uk",
            resources=[
                {
                    "url": "http://test.com/",
                    "custom_resource_text": "my custom resource",
                }
            ],
        )
        result = helpers.call_action("package_show", name_or_id="test_package")
        assert (
            "my custom resource"
            == result["resources"][0]["custom_resource_text"]
        )
        assert (
            "my custom resource"
            == result["resources"][0]["custom_resource_text"]
        )


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform")
@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
class TestCustomSearch(object):
    def test_custom_search(self, app):
        helpers.call_action(
            "package_create", name="test_package_a", custom_text="z"
        )
        helpers.call_action(
            "package_create", name="test_package_b", custom_text="y"
        )

        response = app.get(
            "/dataset/", query_string={"sort": "custom_text asc"}
        )

        # check that package_b appears before package a (y < z)
        a = six.ensure_text(response.data).index("test_package_a")
        b = six.ensure_text(response.data).index("test_package_b")
        assert b < a

        response = app.get(
            "/dataset/", query_string={"sort": "custom_text desc"}
        )
        # check that package_a appears before package b (z is first in
        # descending order)
        a = six.ensure_text(response.data).index("test_package_a")
        b = six.ensure_text(response.data).index("test_package_b")
        assert a < b
