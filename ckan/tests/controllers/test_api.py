# encoding: utf-8
"""
NB Don't test logic functions here. This is just for the mechanics of the API
controller itself.
"""
import json
import re

import pytest
import six

from ckan.lib.helpers import url_for
import ckan.tests.helpers as helpers
from ckan.tests import factories
from ckan.lib import uploader as ckan_uploader


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestApiController(object):
    def test_resource_create_upload_file(
            self, app, monkeypatch, tmpdir, ckan_config):
        monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan_uploader, u'_storage_path', str(tmpdir))

        user = factories.User()
        pkg = factories.Dataset(creator_user_id=user["id"])

        url = url_for(
            controller="api",
            action="action",
            logic_function="resource_create",
            ver="/3",
        )
        env = {"REMOTE_USER": six.ensure_str(user["name"])}

        content = six.ensure_binary('upload-content')
        upload_content = six.BytesIO(content)
        postparams = {
            "name": "test-flask-upload",
            "package_id": pkg["id"],
            "upload": (upload_content, "test-upload.txt")}

        resp = app.post(
            url,
            data=postparams,
            environ_overrides=env,
            content_type='multipart/form-data'
        )
        result = resp.json["result"]
        assert "upload" == result["url_type"]
        assert len(content) == result["size"]

    def test_unicode_in_error_message_works_ok(self, app):
        # Use tag_delete to echo back some unicode

        org_url = "/api/action/tag_delete"
        data_dict = {"id": u"Delta symbol: \u0394"}  # unicode gets rec'd ok
        response = app.post(url=org_url, data=data_dict, status=404)
        # The unicode is backslash encoded (because that is the default when
        # you do str(exception) )
        assert helpers.body_contains(response, "Delta symbol: \\u0394")

    @pytest.mark.usefixtures("clean_index")
    def test_dataset_autocomplete_name(self, app):
        dataset = factories.Dataset(name="rivers")
        url = url_for(
            controller="api", action="dataset_autocomplete", ver="/2"
        )
        assert url == "/api/2/util/dataset/autocomplete"

        response = app.get(url=url, query_string={"incomplete": u"rive"}, status=200)

        results = json.loads(response.body)
        assert results == {
            u"ResultSet": {
                u"Result": [
                    {
                        u"match_field": u"name",
                        u"name": u"rivers",
                        u"match_displayed": u"rivers",
                        u"title": dataset["title"],
                    }
                ]
            }
        }
        assert (
            response.headers["Content-Type"]
            == "application/json;charset=utf-8"
        )

    @pytest.mark.usefixtures("clean_index")
    def test_dataset_autocomplete_title(self, app):
        dataset = factories.Dataset(name="test_ri", title="Rivers")
        url = url_for(
            controller="api", action="dataset_autocomplete", ver="/2"
        )
        assert url == "/api/2/util/dataset/autocomplete"

        response = app.get(url=url, query_string={"incomplete": u"riv"}, status=200)

        results = json.loads(response.body)
        assert results == {
            u"ResultSet": {
                u"Result": [
                    {
                        u"match_field": u"title",
                        u"name": dataset["name"],
                        u"match_displayed": u"Rivers (test_ri)",
                        u"title": u"Rivers",
                    }
                ]
            }
        }
        assert (
            response.headers["Content-Type"]
            == "application/json;charset=utf-8"
        )

    def test_tag_autocomplete(self, app):
        factories.Dataset(tags=[{"name": "rivers"}])
        url = url_for(controller="api", action="tag_autocomplete", ver="/2")
        assert url == "/api/2/util/tag/autocomplete"

        response = app.get(url=url, query_string={"incomplete": u"rive"}, status=200)

        results = json.loads(response.body)
        assert results == {"ResultSet": {"Result": [{"Name": "rivers"}]}}
        assert (
            response.headers["Content-Type"]
            == "application/json;charset=utf-8"
        )

    def test_group_autocomplete_by_name(self, app):
        org = factories.Group(name="rivers", title="Bridges")
        url = url_for(controller="api", action="group_autocomplete", ver="/2")
        assert url == "/api/2/util/group/autocomplete"

        response = app.get(url=url, query_string={"q": u"rive"}, status=200)

        results = json.loads(response.body)
        assert len(results) == 1
        assert results[0]["name"] == "rivers"
        assert results[0]["title"] == "Bridges"
        assert (
            response.headers["Content-Type"]
            == "application/json;charset=utf-8"
        )

    def test_group_autocomplete_by_title(self, app):
        org = factories.Group(name="frogs", title="Bugs")
        url = url_for(controller="api", action="group_autocomplete", ver="/2")

        response = app.get(url=url, query_string={"q": u"bug"}, status=200)

        results = json.loads(response.body)
        assert len(results) == 1
        assert results[0]["name"] == "frogs"

    def test_organization_autocomplete_by_name(self, app):
        org = factories.Organization(name="simple-dummy-org")
        url = url_for(
            controller="api", action="organization_autocomplete", ver="/2"
        )
        assert url == "/api/2/util/organization/autocomplete"

        response = app.get(url=url, query_string={"q": u"simple"}, status=200)

        results = json.loads(response.body)
        assert len(results) == 1
        assert results[0]["name"] == "simple-dummy-org"
        assert results[0]["title"] == org["title"]
        assert (
            response.headers["Content-Type"]
            == "application/json;charset=utf-8"
        )

    def test_organization_autocomplete_by_title(self, app):
        org = factories.Organization(title="Simple dummy org")
        url = url_for(
            controller="api", action="organization_autocomplete", ver="/2"
        )

        response = app.get(url=url, query_string={"q": u"simple dum"}, status=200)

        results = json.loads(response.body)
        assert len(results) == 1
        assert results[0]["title"] == "Simple dummy org"

    def test_config_option_list_access_sysadmin(self, app):
        user = factories.Sysadmin()
        url = url_for(
            controller="api",
            action="action",
            logic_function="config_option_list",
            ver="/3",
        )

        app.get(
            url=url,
            query_string={},
            environ_overrides={"REMOTE_USER": six.ensure_str(user["name"])},
            status=200,
        )

    def test_config_option_list_access_sysadmin_jsonp(self, app):
        user = factories.Sysadmin()
        url = url_for(
            controller="api",
            action="action",
            logic_function="config_option_list",
            ver="/3",
        )

        app.get(
            url=url,
            query_string={"callback": "myfn"},
            environ_overrides={"REMOTE_USER": six.ensure_str(user["name"])},
            status=403,
        )

    def test_jsonp_works_on_get_requests(self, app):

        dataset1 = factories.Dataset()
        dataset2 = factories.Dataset()

        url = url_for(
            controller="api",
            action="action",
            logic_function="package_list",
            ver="/3",
        )

        res = app.get(url=url, query_string={"callback": "my_callback"})
        assert re.match(r"my_callback\(.*\);", six.ensure_str(res.body)), res
        # Unwrap JSONP callback (we want to look at the data).
        start = len("my_callback") + 1
        msg = res.body[start:-2]
        res_dict = json.loads(msg)
        assert res_dict["success"]
        assert sorted(res_dict["result"]) == sorted(
            [dataset1["name"], dataset2["name"]]
        )

    def test_jsonp_returns_javascript_content_type(self, app):
        url = url_for(
            controller="api",
            action="action",
            logic_function="status_show",
            ver="/3",
        )

        res = app.get(url=url, query_string={"callback": "my_callback"})
        assert "application/javascript" in res.headers.get("Content-Type")

    def test_jsonp_does_not_work_on_post_requests(self, app):

        dataset1 = factories.Dataset()
        dataset2 = factories.Dataset()

        url = url_for(
            controller="api",
            action="action",
            logic_function="package_list",
            ver="/3",
            callback="my_callback",
        )

        res = app.post(url=url)
        # The callback param is ignored and the normal response is returned
        assert not six.ensure_str(res.body).startswith("my_callback")
        res_dict = json.loads(res.body)
        assert res_dict["success"]
        assert sorted(res_dict["result"]) == sorted(
            [dataset1["name"], dataset2["name"]]
        )


def test_i18n_only_known_locales_are_accepted(app):

    url = url_for("api.i18n_js_translations", ver=2, lang="fr")

    assert app.get(url).status_code == 200

    url = url_for("api.i18n_js_translations", ver=2, lang="unknown_lang")
    r = app.get(url, status=400)
    assert "Bad request - Unknown locale" in r.get_data(as_text=True)
