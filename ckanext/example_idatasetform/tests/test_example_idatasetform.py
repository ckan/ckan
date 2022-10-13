# encoding: utf-8

import pytest
import six
import bs4

from unittest import mock
from ckan.lib.helpers import url_for

import ckan.plugins as plugins
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckanext.example_idatasetform as idf
import ckan.model as model


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

    def test_custom_field_with_extras(self):
        dataset = factories.Dataset(
            type='fancy_type',
            name='test-dataset',
            custom_text='custom-text',
            extras=[
                {'key': 'key1', 'value': 'value1'},
                {'key': 'key2', 'value': 'value2'},
            ]
        )
        assert dataset['custom_text'] == 'custom-text'
        assert dataset['extras'] == [
            {'key': 'key1', 'value': 'value1'},
            {'key': 'key2', 'value': 'value2'},
        ]

    def test_mixed_extras(self):
        dataset = factories.Dataset(
            type='fancy_type',
            name='test-dataset',
            custom_text='custom-text',
            extras=[
                {'key': 'key1', 'value': 'value1'},
                {'key': 'custom_text_2', 'value': 'custom-text-2'},
                {'key': 'key2', 'value': 'value2'},
            ],
        )
        assert dataset['custom_text'] == 'custom-text'
        assert dataset['custom_text_2'] == 'custom-text-2'
        assert dataset['extras'] == [
            {'key': 'key1', 'value': 'value1'},
            {'key': 'key2', 'value': 'value2'},
        ]


@pytest.fixture
def user():
    user = factories.UserWithToken()
    return user


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v5")
@pytest.mark.ckan_config("package_edit_return_url", None)
@pytest.mark.usefixtures(
    "clean_db", "clean_index", "with_plugins", "with_request_context"
)
class TestUrlsForCustomDatasetType(object):
    def test_dataset_create_redirects(self, app, user):
        name = "fancy-urls"
        env = {"Authorization": user["token"]}
        resp = app.post(
            url_for("fancy_type.new"),
            data={"name": name, "save": "", "_ckan_phase": 1},
            extra_environ=env,
            follow_redirects=False,
        )
        assert resp.location == url_for(
            "fancy_type_resource.new", id=name, _external=True
        )

        res_form_url = url_for("fancy_type_resource.new", id=name)
        resp = app.post(
            res_form_url,
            data={"id": "", "url": "", "save": "go-dataset", "_ckan_phase": 2},
            follow_redirects=False,
            extra_environ=env
        )
        assert resp.location == url_for(
            "fancy_type.edit", id=name, _external=True
        )

        resp = app.post(
            res_form_url,
            data={"id": "", "url": "", "save": "again", "_ckan_phase": 2},
            follow_redirects=False,
            extra_environ=env
        )

        assert resp.location == url_for(
            "fancy_type_resource.new", id=name, _external=True
        )
        resp = app.post(
            res_form_url,
            data={
                "id": "",
                "url": "",
                "save": "go-metadata",
                "_ckan_phase": 2,
            },
            extra_environ=env,
            follow_redirects=False,
        )

        assert resp.location == url_for(
            "fancy_type.read", id=name, _external=True
        )

    def test_links_on_edit_pages(self, app):
        user = factories.Sysadmin()

        pkg = factories.Dataset(type="fancy_type", user=user)
        res = factories.Resource(package_id=pkg["id"], user=user)
        response = app.get(
            url_for("fancy_type.edit", id=pkg["name"]),
            environ_overrides={"REMOTE_USER": user["name"]},
            status=200,
        )
        page = bs4.BeautifulSoup(response.body)
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
            environ_overrides={"REMOTE_USER": user["name"]},
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
                ),
                environ_overrides={"REMOTE_USER": user["name"]},
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
            environ_overrides={"REMOTE_USER": user["name"]},
            data={"id": res["id"], "url": res["url"], "save": "go-metadata"},
            follow_redirects=False,
        )
        assert resp.location == url_for(
            "fancy_type_resource.read",
            id=pkg["name"],
            resource_id=res["id"],
            _external=True,
        )

    @mock.patch("flask_login.utils._get_user")
    def test_links_on_read_pages(self, current_user, app):
        user = factories.User()
        user_obj = model.User.get(user["name"])
        # mock current_user
        current_user.return_value = user_obj

        pkg = factories.Dataset(type="fancy_type", user=user)
        res = factories.Resource(package_id=pkg["id"], user=user)
        page = bs4.BeautifulSoup(
            app.get(
                url_for("fancy_type.read", id=pkg["name"])).body
        )
        page_header = page.find(class_="page-header")
        for action in ["read", "groups", "edit"]:
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


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v6")
@pytest.mark.usefixtures("with_plugins", "with_request_context")
class TestDatasetBlueprintPreparations(object):
    def test_additional_routes_are_registered(self, app):
        resp = app.get("/fancy_type/fancy-route", status=200)
        assert resp.body == u'Hello, fancy_type'

    def test_existing_routes_are_replaced(self, app):
        resp = app.get("/fancy_type/new", status=200)
        assert resp.body == u'Hello, new fancy_type'

        resp = app.get("/fancy_type/random/resource/new", status=200)
        assert resp.body == u'Hello, fancy_type:random'

    @pytest.mark.usefixtures(u'clean_db', u'clean_index')
    def test_existing_routes_are_untouched(self, app):
        resp = app.get("/fancy_type", status=200)
        page = bs4.BeautifulSoup(resp.body)
        links = [
            a['href'] for a in page.select(".breadcrumb a")
        ]
        assert links == ['/', '/fancy_type/']


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_v7")
@pytest.mark.usefixtures("with_plugins", "with_request_context")
class TestDatasetMultiTypes(object):
    @pytest.mark.parametrize('type_', ['first', 'second'])
    def test_untouched_routes(self, type_, app):
        resp = app.get('/' + type_, status=200)
        page = bs4.BeautifulSoup(resp.body)
        assert page.body.header

    @pytest.mark.usefixtures('clean_db')
    @pytest.mark.parametrize('type_', ['first', 'second'])
    def test_template_without_options(self, type_, app, user):
        env = {"Authorization": user["token"]}
        resp = app.get(
            '/{}/new'.format(type_), extra_environ=env, status=200)
        assert resp.body == 'new package form'

    @pytest.mark.usefixtures('clean_db')
    @pytest.mark.parametrize('type_', ['first', 'second'])
    def test_template_with_options(self, type_, app):
        dataset = factories.Dataset(type=type_)
        url = url_for(type_ + '.read', id=dataset['name'])
        resp = app.get(url, status=200)
        assert resp.body == 'Hello, {}!'.format(type_)


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform_inherit")
@pytest.mark.usefixtures("with_plugins")
def test_validation_works_on_default_validate():

    dataset = factories.Dataset(name="my_dataset", type="custom_dataset")

    assert dataset["name"] == "my_dataset"
