from __future__ import annotations

from typing import Any
from faker import Faker
from file_keeper.core.upload import BytesIO
import pytest
import ckan.lib.helpers as h
import ckan.plugins as plugins
import ckan.tests.factories as factories
from ckan import types
from ckan.tests.helpers import call_action


@pytest.mark.ckan_config("ckan.plugins", "test_resource_view")
@pytest.mark.ckan_config("ckan.views.default_views", "test_resource_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestPluggablePreviews:
    def test_hook(self, app):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        res = factories.Resource(package_id=dataset["id"])
        plugin = plugins.get_plugin("test_resource_view")
        plugin.calls.clear()

        url = h.url_for(
            "{}_resource.read".format(dataset["type"]),
            id=res["package_id"], resource_id=res["id"]
        )
        result = app.get(url)
        assert "There are no views created" in result

        # no preview for type "ümlaut", should not fail
        res["format"] = u"ümlaut"
        call_action("resource_update", **res)
        result = app.get(url, status=200)
        assert "There are no views created" in result

        res["format"] = "mock"
        call_action("resource_update", **res)

        assert plugin.calls["can_view"] == 2

        result = app.get(url)

        assert 'data-module="data-viewer"' in result.body
        assert "<iframe" in result.body

        views = call_action("resource_view_list", id=res["id"])

        assert len(views) == 1
        assert views[0]["view_type"] == "test_resource_view"

        view_url = h.url_for(
            "{}_resource.view".format(dataset["type"]),
            id=res["package_id"], resource_id=res["id"], view_id=views[0]["id"]
        )

        result = app.get(view_url)

        assert plugin.calls["setup_template_variables"] == 1
        assert plugin.calls["view_template"] == 1

        assert "mock-preview" in result
        assert "mock-preview.js" in result


@pytest.mark.usefixtrues("with_plugins", "non_clean_db")
class TestCreate:
    """Tests for the resource creation page."""

    def test_empty_form(
        self, user: dict[str, Any], app: types.FixtureApp, package: dict[str, Any]
    ):
        """Submitting an empty resource form does not create a resource."""
        app.set_session_user(user["name"])

        # when form is submitted, even if `upload` field is empty, it's sent to
        # flask as unnamed file with no content. To reliably test creation of
        # empty resource, `upload` must be provided in the same way in the
        # following payload.
        app.post(
            f"/dataset/{package['name']}/resource/new",
            data={"save": "", "id": "", "upload": (BytesIO(), "")},
        )

        pkg = call_action("package_show", id=package["id"])
        assert not pkg["resources"]

    def test_form_with_upload(
        self,
        user: dict[str, Any],
        app: types.FixtureApp,
        package: dict[str, Any],
        faker: Faker,
    ):
        """Submitting a resource form with an uploaded file creates a new resource."""
        content = faker.binary(42)
        filename = faker.file_name(extension="txt")
        app.set_session_user(user["name"])
        app.post(
            f"/dataset/{package['name']}/resource/new",
            data={"save": "", "id": "", "upload": (BytesIO(content), filename)},
        )

        pkg = call_action("package_show", id=package["id"])

        assert len(pkg["resources"]) == 1
        res = pkg["resources"][0]

        assert res["size"] == len(content)
        assert res["format"] == "TXT"
        assert res["url"].endswith(filename)
