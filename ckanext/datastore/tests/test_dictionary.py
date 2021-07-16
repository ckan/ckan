# encoding: utf-8

import pytest
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config("ckan.plugins", "datastore datapusher")
@pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
def test_read(app):
    user = factories.User()
    dataset = factories.Dataset(creator_user_id=user["id"])
    resource = factories.Resource(
        package_id=dataset["id"], creator_user_id=user["id"]
    )
    data = {
        "resource_id": resource["id"],
        "force": True,
        "records": [
            {"from": "Brazil", "to": "Brazil", "num": 2},
            {"from": "Brazil", "to": "Italy", "num": 22},
        ],
    }
    helpers.call_action("datastore_create", **data)
    auth = {"Authorization": str(user["apikey"])}
    app.get(
        url="/dataset/{id}/dictionary/{resource_id}".format(
            id=str(dataset["name"]), resource_id=str(resource["id"])
        ),
        extra_environ=auth,
    )
