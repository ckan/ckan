# encoding: utf-8

import pytest
import six
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.lib import helpers as template_helpers


@pytest.mark.ckan_config("ckan.plugins", "datastore")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
def test_info_success():
    resource = factories.Resource()
    data = {
        "resource_id": resource["id"],
        "force": True,
        "records": [
            {"from": "Brazil", "to": "Brazil", "num": 2},
            {"from": "Brazil", "to": "Italy", "num": 22},
        ],
    }
    helpers.call_action("datastore_create", **data)

    # aliases can only be created against an existing resource
    data = {
        "resource_id": resource["id"],
        "force": True,
        "aliases": "testalias1, testview2",

    }
    helpers.call_action("datastore_create", **data)

    info = helpers.call_action("datastore_info", id=resource["id"])

    assert len(info["meta"]) == 7, info["meta"]
    assert info["meta"]["count"] == 2
    assert info["meta"]["table_type"] == "BASE TABLE"
    assert len(info["meta"]["aliases"]) == 2
    assert info["meta"]["aliases"] == ["testview2", "testalias1"]
    assert len(info["fields"]) == 3, info["fields"]
    assert info["fields"][0]["id"] == "from"
    assert info["fields"][0]["type"] == "text"
    assert info["fields"][0]["schema"]["native_type"] == "text"
    assert not info["fields"][0]["schema"]["is_index"]
    assert info["fields"][2]["id"] == "num"
    assert info["fields"][2]["schema"]["native_type"] == "integer"

    # check datastore_info with alias
    info = helpers.call_action("datastore_info", id='testalias1')

    assert len(info["meta"]) == 7, info["meta"]
    assert info["meta"]["count"] == 2
    assert info["meta"]["id"] == resource["id"]


@pytest.mark.ckan_config("ckan.plugins", "datastore")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
def test_api_info(app):
    dataset = factories.Dataset()
    resource = factories.Resource(
        id="588dfa82-760c-45a2-b78a-e3bc314a4a9b",
        package_id=dataset["id"],
        datastore_active=True,
    )

    # the 'API info' is seen on the resource_read page, a snippet loaded by
    # javascript via data_api_button.html
    url = template_helpers.url_for(
        "api.snippet",
        ver=1,
        snippet_path="api_info.html",
        resource_id=resource["id"],
    )

    page = app.get(url, status=200)

    # check we built all the urls ok
    expected_urls = (
        "http://test.ckan.net/api/3/action/datastore_create",
        "http://test.ckan.net/api/3/action/datastore_upsert",
        "<code>http://test.ckan.net/api/3/action/datastore_search",
        "http://test.ckan.net/api/3/action/datastore_search_sql",
        "url: 'http://test.ckan.net/api/3/action/datastore_search'",
        "http://test.ckan.net/api/3/action/datastore_search"
    )
    content = six.ensure_text(page.data)
    for url in expected_urls:
        assert url in content
