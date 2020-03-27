# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

import pytest
import six
from freezegun import freeze_time

import ckan.model as model
import ckan.plugins.toolkit as tk
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.lib.helpers import url_for


@pytest.mark.ckan_config(u"ckan.plugins", u"expire_api_token")
@pytest.mark.usefixtures(u"clean_db", u"with_plugins")
class TestExpireApiTokenPlugin(object):
    def test_token_is_removed_on_second_use(self, app):
        user = factories.User()
        now = datetime.now()
        token = helpers.call_action(
            u"api_token_create",
            context={u"model": model, u"user": user[u"name"]},
            user=user[u"name"],
            name=u"token-name",
            expires_at=(now + timedelta(days=1)).strftime(u"%Y-%m-%d"),
        )

        data = tk.jwt_decode(token)
        id = data["token"]
        assert model.ApiToken.get(id)

        app.get(
            url_for(u"user.api_tokens", id=user["id"]),
            headers={u"authorization": six.ensure_str(token)},
        )
        assert model.ApiToken.get(id)

        with freeze_time(now + timedelta(days=2)):
            app.get(
                url_for(u"user.api_tokens", id=user["id"]),
                headers={u"authorization": six.ensure_str(token)},
                status=403,
            )
            assert not model.ApiToken.get(id)
