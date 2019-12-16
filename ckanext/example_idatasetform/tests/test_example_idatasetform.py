# encoding: utf-8

import pytest
from ckan.common import config

from ckan.lib.helpers import url_for

import ckan.model as model
import ckan.plugins as plugins
import ckan.tests.helpers as helpers
import ckanext.example_idatasetform as idf
import ckan.lib.search


class ExampleIDatasetFormPluginBase(helpers.FunctionalTestBase):
    """Version 1, 2 and 3 of the plugin are basically the same, so this class
    provides the tests that all three versions of the plugins will run"""

    def teardown(self):
        model.repo.rebuild_db()
        ckan.lib.search.clear_all()

    @classmethod
    def teardown_class(cls):
        ckan.lib.search.clear_all()
        super(ExampleIDatasetFormPluginBase, cls).teardown_class()

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


class TestVersion1(ExampleIDatasetFormPluginBase):
    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg["ckan.plugins"] = "example_idatasetform_v1"

    @classmethod
    def teardown_class(cls):
        plugins.unload("example_idatasetform_v1")
        super(TestVersion1, cls).teardown_class()


class TestVersion2(ExampleIDatasetFormPluginBase):
    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg["ckan.plugins"] = "example_idatasetform_v2"

    @classmethod
    def teardown_class(cls):
        plugins.unload("example_idatasetform_v2")
        super(TestVersion2, cls).teardown_class()


class TestVersion3(ExampleIDatasetFormPluginBase):
    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg["ckan.plugins"] = "example_idatasetform_v3"

    @classmethod
    def teardown_class(cls):
        plugins.unload("example_idatasetform_v3")
        super(TestVersion3, cls).teardown_class()


class TestVersion5(helpers.FunctionalTestBase):
    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg["ckan.plugins"] = "example_idatasetform_v5"

    def teardown(self):
        if plugins.plugin_loaded("example_idatasetform_v5"):
            plugins.unload("example_idatasetform_v5")

    def test_custom_package_type_urls(self):
        assert url_for("fancy_type.search") == "/fancy_type/"
        assert url_for("fancy_type.new") == "/fancy_type/new"
        assert url_for("fancy_type.read", id="check") == "/fancy_type/check"
        assert (
            url_for("fancy_type.edit", id="check") == "/fancy_type/edit/check"
        )


class TestIDatasetFormPluginVersion4(helpers.FunctionalTestBase):
    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg["ckan.plugins"] = "example_idatasetform_v4"

    def teardown(self):
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        if plugins.plugin_loaded("example_idatasetform_v4"):
            plugins.unload("example_idatasetform_v4")
        ckan.lib.search.clear_all()
        super(TestIDatasetFormPluginVersion4, cls).teardown_class()

    def test_package_create(self):
        idf.plugin_v4.create_country_codes()
        result = helpers.call_action(
            "package_create",
            name="test_package",
            custom_text="this is my custom text",
            country_code="uk",
        )
        assert "this is my custom text" == result["custom_text"]
        assert [u"uk"] == result["country_code"]

    def test_package_create_wrong_country_code(self):
        idf.plugin_v4.create_country_codes()
        with pytest.raises(plugins.toolkit.ValidationError):
            helpers.call_action(
                "package_create",
                name="test_package",
                custom_text="this is my custom text",
                country_code="notcode",
            )

    def test_package_update(self):
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


class TestIDatasetFormPlugin(helpers.FunctionalTestBase):
    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg["ckan.plugins"] = "example_idatasetform"

    def teardown(self):
        model.repo.rebuild_db()
        ckan.lib.search.clear_all()

    @classmethod
    def teardown_class(cls):
        plugins.unload("example_idatasetform")
        ckan.lib.search.clear_all()
        super(TestIDatasetFormPlugin, cls).teardown_class()

    def test_package_create(self):
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

    def test_package_update(self):
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

    def test_package_show(self):
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


class TestCustomSearch(object):
    # @classmethod
    # def _apply_config_changes(cls, cfg):
    #     cfg['ckan.plugins'] = 'example_idatasetform'

    @classmethod
    def setup_class(cls):
        cls.original_config = config.copy()
        config["ckan.plugins"] = "example_idatasetform"

    def teardown(self):
        model.repo.rebuild_db()
        ckan.lib.search.clear_all()

    @classmethod
    def teardown_class(cls):
        if plugins.plugin_loaded("example_idatasetform"):
            plugins.unload("example_idatasetform")
        helpers.reset_db()
        ckan.lib.search.clear_all()

        config.clear()
        config.update(cls.original_config)

    def test_custom_search(self):
        app = helpers._get_test_app()

        helpers.call_action(
            "package_create", name="test_package_a", custom_text="z"
        )
        helpers.call_action(
            "package_create", name="test_package_b", custom_text="y"
        )

        response = app.get("/dataset/")

        # change the sort by form to our custom_text ascending
        response.forms[1].fields["sort"][0].value = "custom_text asc"

        response = response.forms[1].submit()
        # check that package_b appears before package a (y < z)
        a = response.body.index("test_package_a")
        b = response.body.index("test_package_b")
        assert b < a

        response = app.get("/dataset/")
        response.forms[1].fields["sort"][0].value = "custom_text desc"
        # check that package_a appears before package b (z is first in
        # descending order)
        response = response.forms[1].submit()
        a = response.body.index("test_package_a")
        b = response.body.index("test_package_b")
        assert a < b
