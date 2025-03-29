# encoding: utf-8

import pytest
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

    info = helpers.call_action(
        "datastore_info", id=resource["id"],
        include_meta=False, include_fields_schema=False)

    assert 'meta' not in info
    assert not any('schema' in f for f in info['fields'])


@pytest.mark.ckan_config("ckan.plugins", "datastore")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
def test_api_info(app):
    resource = factories.Resource()
    data = {
        "resource_id": resource["id"],
        "force": True,
        "records": [
            {"from": "Brazil", "to": "Brazil", "num": 2},
        ],
    }
    helpers.call_action("datastore_create", **data)

    # the 'API info' is seen on the resource_read page, a snippet loaded by
    # javascript via data_api_button.html
    url = template_helpers.url_for(
        "datastore.api_info",
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
