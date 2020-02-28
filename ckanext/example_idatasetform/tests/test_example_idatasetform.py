# encoding: utf-8

import pytest
import six
import bs4
from ckan.common import config

from ckan.lib.helpers import url_for

import ckan.model as model
import ckan.plugins as plugins
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
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
@pytest.mark.usefixtures(
    "clean_db", "clean_index", "with_plugins", "with_request_context"
)
class TestVersion5(object):
    def test_custom_package_type_urls(self):
        assert url_for("fancy_type.search") == "/fancy_type/"
        assert url_for("fancy_type.new") == "/fancy_type/new"
        assert url_for("fancy_type.read", id="check") == "/fancy_type/check"
        assert (
            url_for("fancy_type.edit", id="check") == "/fancy_type/edit/check"
        )


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v5")
@pytest.mark.ckan_config("package_edit_return_url", None)
@pytest.mark.usefixtures(
    "clean_db", "clean_index", "with_plugins", "with_request_context"
)
class TestUrlsForCustomDatasetType(object):
    def test_dataset_create_redirects(self, app):
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        name = "fancy-urls"

        resp = app.post(
            url_for("fancy_type.new"),
            environ_overrides=env,
            data={"name": name, "save": "", "_ckan_phase": 1},
            follow_redirects=False,
        )
        assert resp.location == url_for(
            "fancy_type_resource.new", id=name, _external=True
        )

        res_form_url = url_for("fancy_type_resource.new", id=name)
        resp = app.post(
            res_form_url,
            environ_overrides=env,
            data={"id": "", "url": "", "save": "go-dataset", "_ckan_phase": 2},
            follow_redirects=False,
        )
        assert resp.location == url_for(
            "fancy_type.edit", id=name, _external=True
        )

        resp = app.post(
            res_form_url,
            environ_overrides=env,
            data={"id": "", "url": "", "save": "again", "_ckan_phase": 2},
            follow_redirects=False,
        )

        assert resp.location == url_for(
            "fancy_type_resource.new", id=name, _external=True
        )
        resp = app.post(
            res_form_url,
            environ_overrides=env,
            data={
                "id": "",
                "url": "",
                "save": "go-metadata",
                "_ckan_phase": 2,
            },
            follow_redirects=False,
        )

        assert resp.location == url_for(
            "fancy_type.read", id=name, _external=True
        )

    def test_links_on_edit_pages(self, app):
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        pkg = factories.Dataset(type="fancy_type", user=user)
        res = factories.Resource(package_id=pkg["id"], user=user)
        page = bs4.BeautifulSoup(
            app.get(
                url_for("fancy_type.edit", id=pkg["name"]), extra_environ=env
            ).body
        )
        page_header = page.find(class_="page-header")
        for action in ["edit", "resources", "read"]:
            assert page_header.find(
                href=url_for("fancy_type." + action, id=pkg["name"])
            )

        assert page.find(id="dataset-edit").find(
            href=url_for("fancy_type.delete", id=pkg["id"],)
        )
        resp = app.post(
            url_for("fancy_type.edit", id=pkg["name"]),
            data={
                "name": pkg["name"],
                "save": "",
                "_ckan_phase": "dataset_new_1",
            },
            follow_redirects=False,
        )
        assert resp.location == url_for(
            "fancy_type.read", id=pkg["name"], _external=True
        )

        breadcrumbs = page.select_one(".breadcrumb")
        assert breadcrumbs.find(href=url_for("fancy_type.search"))
        assert breadcrumbs.find(
            href=url_for("fancy_type.read", id=pkg["name"])
        )
        assert breadcrumbs.find(
            href=url_for("fancy_type.edit", id=pkg["name"])
        )

        # And check links of package's resource
        page = bs4.BeautifulSoup(
            app.get(
                url_for(
                    "fancy_type_resource.edit",
                    id=pkg["id"],
                    resource_id=res["id"],
                )
            ).body
        )
        page_header = page.find(class_="page-header")
        for action in ["edit", "views", "read"]:
            assert page_header.find(
                href=url_for(
                    "fancy_type_resource." + action,
                    id=pkg["name"],
                    resource_id=res["id"],
                )
            )

        breadcrumbs = page.select_one(".breadcrumb")
        assert breadcrumbs.find(href=url_for("fancy_type.search"))
        assert breadcrumbs.find(
            href=url_for("fancy_type.read", id=pkg["name"])
        )
        assert breadcrumbs.find(
            href=url_for(
                "fancy_type_resource.read",
                id=pkg["name"],
                resource_id=res["id"],
            )
        )
        resp = app.post(
            url_for(
                "fancy_type_resource.edit",
                id=pkg["name"],
                resource_id=res["id"],
            ),
            data={"id": res["id"], "url": res["url"], "save": "go-metadata"},
            follow_redirects=False,
        )
        assert resp.location == url_for(
            "fancy_type_resource.read",
            id=pkg["name"],
            resource_id=res["id"],
            _external=True,
        )

    def test_links_on_read_pages(self, app):
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        pkg = factories.Dataset(type="fancy_type", user=user)
        res = factories.Resource(package_id=pkg["id"], user=user)
        page = bs4.BeautifulSoup(
            app.get(
                url_for("fancy_type.read", id=pkg["name"]), extra_environ=env
            ).body
        )
        page_header = page.find(class_="page-header")
        for action in ["read", "groups", "activity", "edit"]:
            assert page_header.find(
                href=url_for("fancy_type." + action, id=pkg["name"])
            )
        # import ipdb; ipdb.set_trace()
        assert page.find(id="dataset-resources").find(
            href=url_for(
                "fancy_type_resource.read",
                id=pkg["name"],
                resource_id=res["id"],
            )
        )

        breadcrumbs = page.select_one(".breadcrumb")
        assert breadcrumbs.find(href=url_for("fancy_type.search"))
        assert breadcrumbs.find(
            href=url_for("fancy_type.read", id=pkg["name"])
        )

        # And check links of package's resource
        page = bs4.BeautifulSoup(
            app.get(
                url_for(
                    "fancy_type_resource.read",
                    id=pkg["id"],
                    resource_id=res["id"],
                )
            ).body
        )
        assert page.find(
            href=url_for(
                "fancy_type_resource.edit",
                id=pkg["name"],
                resource_id=res["id"],
            )
        )

        assert page.find(class_="resources").find(
            href=url_for(
                "fancy_type_resource.read",
                id=pkg["name"],
                resource_id=res["id"],
                inner_span=True,
            )
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
