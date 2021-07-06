# encoding: utf-8

from unittest import mock
import pytest

import ckan.tests.factories as factories
from ckan.logic import _actions


@pytest.mark.ckan_config(u"ckan.plugins", u"datapusher datastore")
@pytest.mark.usefixtures(u"clean_db", u"with_plugins", u"with_request_context")
def test_resource_data(app, monkeypatch):
    user = factories.User()
    dataset = factories.Dataset(creator_user_id=user["id"])
    resource = factories.Resource(
        package_id=dataset["id"], creator_user_id=user["id"]
    )
    auth = {u"REMOTE_USER": user["name"]}

    url = u"/dataset/{id}/resource_data/{resource_id}".format(
        id=str(dataset["name"]), resource_id=str(resource["id"])
    )

    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)
    app.post(url=url, environ_overrides=auth, status=200)
    func.assert_called()
    func.reset_mock()

    app.get(url=url, environ_overrides=auth, status=200)
    func.assert_not_called()
