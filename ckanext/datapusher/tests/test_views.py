from unittest import mock
import pytest

import ckan.tests.factories as factories
from ckan.logic import _actions
from ckanext.datapusher.tests import get_api_token


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.ckan_config("ckan.datapusher.api_token", get_api_token())
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resource_data(app, monkeypatch):
    user = factories.UserWithToken()
    org = factories.Organization(users=[{"name": user["name"], "capacity": "admin"}])

    dataset = factories.Dataset(owner_org=org["id"])
    resource = factories.Resource(package_id=dataset["id"])

    url = "/dataset/{id}/resource_data/{resource_id}".format(
        id=str(dataset["name"]), resource_id=str(resource["id"])
    )

    headers = {"Authorization": user["token"]}
    func = mock.Mock()
    monkeypatch.setitem(_actions, "datapusher_submit", func)
    app.post(url=url, headers=headers, status=200)
    func.assert_called()
    func.reset_mock()

    app.get(url=url, headers=headers, status=200)
    func.assert_not_called()
