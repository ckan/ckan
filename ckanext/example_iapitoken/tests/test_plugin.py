# -*- coding: utf-8 -*-

import json
import pytest
import six

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config(u"ckan.plugins", u"example_iapitoken")
@pytest.mark.usefixtures(u"non_clean_db", u"with_plugins")
class TestIApiTokenPlugin(object):
    def test_token_is_encoded(self):
        user = factories.User()
        data = helpers.call_action(
            u"api_token_create",
            context={u"model": model, u"user": user[u"name"]},
            user=user[u"name"],
            name=u"token-name",
        )
        decoded = json.loads(data[u"token"])
        assert decoded[u"jti"].startswith(u"!")
        assert decoded[u"jti"].endswith(u"!")

    def test_extra_info_available(self):
        user = factories.User()
        data = helpers.call_action(
            u"api_token_create",
            context={u"model": model, u"user": user[u"name"]},
            user=user[u"name"],
            name=u"token-name",
        )
        assert data[u"hello"] == u"world"

    def test_token_is_removed_on_second_use(self, app):
        user = factories.User()
        data = helpers.call_action(
            u"api_token_create",
            context={u"model": model, u"user": user[u"name"]},
            user=user[u"name"],
            name=u"token-name",
        )

        decoded = json.loads(data[u"token"])
        jti = decoded[u"jti"][1:-1]
        obj = model.ApiToken.get(jti)
        assert obj is not None
        assert obj.last_access is None

        app.get(
            tk.h.url_for(u"api.action", logic_function=u"user_show", ver=3),
            params={u"id": user[u"id"]},
            headers={u"authorization": six.ensure_str(data[u"token"])},
        )

        obj = model.ApiToken.get(jti)
        assert obj is not None
        assert obj.last_access is not None

        app.get(
            tk.h.url_for(u"api.action", logic_function=u"user_show", ver=3),
            params={u"id": user[u"id"]},
            headers={u"authorization": six.ensure_str(data[u"token"])},
        )

        obj = model.ApiToken.get(jti)
        assert obj is None
