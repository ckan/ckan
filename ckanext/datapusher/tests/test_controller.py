# encoding: utf-8

import pytest

import ckan.tests.factories as factories
import ckan.tests.legacy as tests


@pytest.mark.ckan_config(u"ckan.plugins", u"datapusher datastore")
@pytest.mark.usefixtures(u"clean_db", u"with_plugins", u"with_request_context")
def test_resource_data(app):
    if not tests.is_datastore_supported():
        pytest.skip(u"Datastore not supported")

    user = factories.User()
    dataset = factories.Dataset(creator_user_id=user["id"])
    resource = factories.Resource(
        package_id=dataset["id"], creator_user_id=user["id"]
    )
    auth = {u"Authorization": str(user["apikey"])}

    app.get(
        url=u"/dataset/{id}/resource_data/{resource_id}".format(
            id=str(dataset["name"]), resource_id=str(resource["id"])
        ),
        extra_environ=auth,
    )
