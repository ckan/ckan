# encoding: utf-8

from unittest import mock
import pytest

import ckan.model as model
from ckan.tests import factories, helpers
from ckan.logic import _actions
from ckanext.datapusher.tests import get_api_token
from ckan.plugins import toolkit


@mock.patch("flask_login.utils._get_user")
@pytest.mark.ckan_config(u"ckan.plugins", u"datapusher datastore")
@pytest.mark.ckan_config("ckan.datapusher.api_token", get_api_token())
@pytest.mark.usefixtures(u"non_clean_db", u"with_plugins")
def test_resource_data(current_user, app, monkeypatch):
    user = factories.User()
    user_obj = model.User.get(user["name"])
    # mock current_user
    current_user.return_value = user_obj

    dataset = factories.Dataset(creator_user_id=user["id"])
    resource = factories.Resource(
        package_id=dataset["id"], creator_user_id=user["id"]
    )

    url = u"/dataset/{id}/resource_data/{resource_id}".format(
        id=str(dataset["name"]), resource_id=str(resource["id"])
    )

    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)
    app.post(url=url, status=200)
    func.assert_called()
    func.reset_mock()

    app.get(url=url, status=200)
    func.assert_not_called()

@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.ckan_config("ckan.datapusher.api_token", get_api_token())
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_datastore_delete(app, monkeypatch):
    """ Does the datastore_delete route remove the table from the datastore """
    user = factories.UserWithToken()
    org = factories.Organization(users=[{"name": user["name"], "capacity": "admin"}])

    dataset = factories.Dataset(owner_org=org["id"])
    resource = factories.Resource(package_id=dataset["id"])

    # Push data directly to the DataStore so it can be deleted
    data = {
        "resource_id": resource["id"],
        "fields": [{"id": "a", "type": "text"}, {"id": "b", "type": "text"}],
        "records": [{"a": "1", "b": "2"}],
        "force": True,
    }
    helpers.call_action("datastore_create", **data)

    assert helpers.call_action("datastore_info", resource_id=resource['id'])

    url = "/dataset/{id}/delete-datastore/{resource_id}".format(
        id=str(dataset["name"]), resource_id=str(resource["id"])
    )

    headers = {"Authorization": user["token"]}
    app.post(url=url, headers=headers, status=200)

    with pytest.raises(toolkit.ObjectNotFound):
        helpers.call_action("datastore_info", resource_id=resource['id'])


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.ckan_config("ckan.datapusher.api_token", get_api_token())
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_datastore_delete_404(app, monkeypatch):
    """ Does the datastore_delete route 404 and not 500 server error on NotFound? """
    user = factories.UserWithToken()
    org = factories.Organization(users=[{"name": user["name"], "capacity": "admin"}])

    dataset = factories.Dataset(owner_org=org["id"])
    resource = factories.Resource(package_id=dataset["id"])

    url = "/dataset/{id}/delete-datastore/{resource_id}".format(
        id=str(dataset["name"]), resource_id="invalid")

    headers = {"Authorization": user["token"]}
    app.post(url=url, headers=headers, status=404)
