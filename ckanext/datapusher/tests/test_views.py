# encoding: utf-8

from unittest import mock
import pytest

import ckan.tests.factories as factories
import ckan.model as model
from ckan.logic import _actions
from ckanext.datapusher.tests import get_api_token


@mock.patch("flask_login.utils._get_user")
@pytest.mark.ckan_config(u"ckan.plugins", u"datapusher datastore")
@pytest.mark.ckan_config("ckan.datapusher.api_token", get_api_token())
@pytest.mark.usefixtures(u"non_clean_db", u"with_plugins", u"with_request_context")
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
