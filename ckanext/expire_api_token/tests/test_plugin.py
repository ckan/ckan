# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

import ckan.model as model
import ckan.lib.api_token as api_token
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.lib.helpers import url_for


@pytest.mark.ckan_config(u"ckan.plugins", u"expire_api_token")
@pytest.mark.usefixtures(u"non_clean_db", u"with_plugins")
class TestExpireApiTokenPlugin(object):
    def test_token_is_removed_on_second_use(self, app):
        user = factories.User()
        now = datetime.now()
        with freeze_time(now):
            data = helpers.call_action(
                u"api_token_create",
                context={u"model": model, u"user": user[u"name"]},
                user=user[u"name"],
                name=u"token-name",
                expires_in=20,
                unit=1,
            )

        decoded = api_token.decode(data["token"])
        id = decoded["jti"]
        assert model.ApiToken.get(id)
        url = url_for("api.action", logic_function=u"api_token_list", ver=3, user=user["id"])
        app.get(
            url, headers={u"authorization": data["token"]},
        )

        with freeze_time(now + timedelta(seconds=22)):
            app.get(
                url,
                headers={u"authorization": data["token"]},
                status=403,
            )

    def test_token_expire(self):
        """ Create a 10 days token and test expiration """
        user = factories.User()
        tests = (
            (90, 1),  # 90 seconds
            (10, 2),  # 10 minutes
            (20, 3),  # 20 hours
            (10, 4),  # 10 days
        )
        for expires_in, unit in tests:
            now = datetime.now()
            now_timestamp = now.timestamp()
            data = helpers.call_action(
                u"api_token_create",
                context={u"model": model, u"user": user[u"name"]},
                user=user[u"name"],
                name=u"token-name",
                expires_in=expires_in,
                unit=unit,
            )
            decoded = api_token.decode(data["token"])
            # Get the timestamp
            expire = decoded["exp"]
            if unit == 1:  # Seconds
                unit_factor = 1
            elif unit == 2:  # Minutes
                unit_factor = 60
            elif unit == 3:  # Hours
                unit_factor = 3600
            elif unit == 4:  # Days
                unit_factor = 86400
            expected = now_timestamp + (expires_in * unit_factor)
            # This won't be exact
            assert abs(expire - expected) < 5
