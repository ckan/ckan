# -*- coding: utf-8 -*-

import json
import pytest
import six

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.plugins.toolkit as tk
from ckan.lib.helpers import url_for


@pytest.mark.ckan_config(u'ckan.plugins', u'example_iapitoken')
@pytest.mark.usefixtures(u'clean_db', u'with_plugins')
class TestIApiTokenPlugin(object):
    def test_token_is_encoded(self):
        user = factories.User()
        token = helpers.call_action(u"api_token_create",
                                    context={
                                        u"model": model,
                                        u"user": user[u"name"]
                                    },
                                    user=user[u"name"],
                                    name=u"token-name")
        data = json.loads(token)
        assert data['token'].startswith(u"!")
        assert data['token'].endswith(u"!")

    def test_token_is_removed_on_second_use(self, app):
        user = factories.User()
        token = helpers.call_action(u"api_token_create",
                                    context={
                                        u"model": model,
                                        u"user": user[u"name"]
                                    },
                                    user=user[u"name"],
                                    name=u"token-name")

        data = json.loads(token)
        real_token = data['token'][1:-1]
        obj = model.ApiToken.get(real_token)
        assert obj is not None
        assert obj.last_access is None

        app.get(url_for(u'api.action', logic_function=u'user_show', ver=3),
                params={u'id': user[u'id']},
                headers={u'authorization': six.ensure_str(token)})

        obj = model.ApiToken.get(real_token)
        assert obj is not None
        assert obj.last_access is not None

        app.get(url_for(u'api.action', logic_function=u'user_show', ver=3),
                params={u'id': user[u'id']},
                headers={u'authorization': six.ensure_str(token)})

        obj = model.ApiToken.get(real_token)
        assert obj is None
