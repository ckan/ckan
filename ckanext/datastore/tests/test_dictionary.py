# encoding: utf-8

import pytest
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config(u"ckan.plugins", u"datastore datapusher")
@pytest.mark.usefixtures(u"clean_datastore", u"with_plugins", u"with_request_context")
def test_read(app):
    user = factories.User()
    dataset = factories.Dataset(creator_user_id=user["id"])
    resource = factories.Resource(
        package_id=dataset["id"], creator_user_id=user["id"]
    )
    data = {
        u"resource_id": resource["id"],
        u"force": True,
        u"records": [
            {u"from": u"Brazil", u"to": u"Brazil", u"num": 2},
            {u"from": u"Brazil", u"to": u"Italy", u"num": 22},
        ],
    }
    helpers.call_action(u"datastore_create", **data)
    auth = {u"Authorization": str(user["apikey"])}
    app.get(
        url=u"/dataset/{id}/dictionary/{resource_id}".format(
            id=str(dataset["name"]), resource_id=str(resource["id"])
        ),
        extra_environ=auth,
    )
