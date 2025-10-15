# encoding: utf-8

import pytest
from ckan.plugins.toolkit import ValidationError
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

    info = helpers.call_action("datastore_info", resource_id=resource["id"])

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
@pytest.mark.usefixtures("with_plugins")
def test_info_missing_id():
    with pytest.raises(ValidationError):
        helpers.call_action("datastore_info")


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

    # check we built some urls, examples properly
    expected_html = (
        "http://test.ckan.net/api/action/datastore_search",
        "http://test.ckan.net/api/action/datastore_search_sql",
        '<pre class="example-curl"><code class="language-bash"',
        f'"sql": "SELECT * FROM \\"{resource["id"]}\\" WHERE',
        "RemoteCKAN('http://test.ckan.net/', apikey=API_TOKEN)",
    )
    content = page.get_data(as_text=True)
    for html in expected_html:
        assert html in content
