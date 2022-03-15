# -*- coding: utf-8 -*-

import pytest
from datetime import datetime

from ckan.model import Session, ApiToken, User
import ckan.tests.factories as factories


@pytest.fixture
def token():
    user = factories.User()
    token = ApiToken(user[u"id"])
    Session.add(token)
    Session.commit()
    return token


@pytest.mark.usefixtures(u"non_clean_db")
class TestApiToken(object):
    def test_new_token_not_accessed(self, token):
        assert token.last_access is None

    def test_token_stores_access_time(self, token):
        before = datetime.utcnow()
        token.touch(True)
        after = datetime.utcnow()

        assert before < token.last_access < after

    def test_tokens_related_to_user(self):
        user_1 = factories.User()
        num_tokens_1 = 5

        user_2 = factories.User()
        num_tokens_2 = 3

        for i in range(num_tokens_1):
            Session.add(ApiToken(user_1[u"id"]))

        for i in range(num_tokens_2):
            Session.add(ApiToken(user_2[u"id"]))

        Session.commit()

        user_1 = User.get(user_1[u"id"])
        assert len(user_1.api_tokens) == num_tokens_1
        for token in user_1.api_tokens:
            assert token.owner == user_1

        user_2 = User.get(user_2[u"id"])
        assert len(user_2.api_tokens) == num_tokens_2
        for token in user_2.api_tokens:
            assert token.owner == user_2
