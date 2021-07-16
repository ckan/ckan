# -*- coding: utf-8 -*-

import json
import pytest
import six

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "example_iapitoken")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestIApiTokenPlugin(object):
    def test_token_is_encoded(self):
        user = factories.User()
        data = helpers.call_action(
            "api_token_create",
            context={"model": model, "user": user["name"]},
            user=user["name"],
            name="token-name",
        )
        decoded = json.loads(data["token"])
        assert decoded["jti"].startswith("!")
        assert decoded["jti"].endswith("!")

    def test_extra_info_available(self):
        user = factories.User()
        data = helpers.call_action(
            "api_token_create",
            context={"model": model, "user": user["name"]},
            user=user["name"],
            name="token-name",
        )
        assert data["hello"] == "world"

    def test_token_is_removed_on_second_use(self, app):
        user = factories.User()
        data = helpers.call_action(
            "api_token_create",
            context={"model": model, "user": user["name"]},
            user=user["name"],
            name="token-name",
        )

        decoded = json.loads(data["token"])
        jti = decoded["jti"][1:-1]
        obj = model.ApiToken.get(jti)
        assert obj is not None
        assert obj.last_access is None

        app.get(
            tk.h.url_for("api.action", logic_function="user_show", ver=3),
            params={"id": user["id"]},
            headers={"authorization": six.ensure_str(data["token"])},
        )

        obj = model.ApiToken.get(jti)
        assert obj is not None
        assert obj.last_access is not None

        app.get(
            tk.h.url_for("api.action", logic_function="user_show", ver=3),
            params={"id": user["id"]},
            headers={"authorization": six.ensure_str(data["token"])},
        )

        obj = model.ApiToken.get(jti)
        assert obj is None
