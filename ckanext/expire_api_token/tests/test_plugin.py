# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

import pytest
import six
from freezegun import freeze_time

import ckan.model as model
import ckan.lib.api_token as api_token
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.lib.helpers import url_for


@pytest.mark.ckan_config("ckan.plugins", "expire_api_token")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestExpireApiTokenPlugin(object):
    def test_token_is_removed_on_second_use(self, app):
        user = factories.User()
        now = datetime.now()
        with freeze_time(now):
            data = helpers.call_action(
                "api_token_create",
                context={"model": model, "user": user["name"]},
                user=user["name"],
                name="token-name",
                expires_in=20,
                unit=1,
            )

        decoded = api_token.decode(data["token"])
        id = decoded["jti"]
        assert model.ApiToken.get(id)

        url = url_for("user.api_tokens", id=user["id"])
        app.get(
            url, headers={"authorization": six.ensure_str(data["token"])},
        )

        with freeze_time(now + timedelta(seconds=22)):
            app.get(
                url,
                headers={"authorization": six.ensure_str(data["token"])},
                status=403,
            )
