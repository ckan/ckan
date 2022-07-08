# encoding: utf-8

import pytest
import ckan.tests.factories as factories
from ckan.lib.authenticator import default_authenticate


@pytest.mark.usefixtures("non_clean_db")
class TestUsernamePasswordAuthenticator(object):
    password = 'somepass'

    def test_succeeds_if_username_and_password_are_correct(self):
        user = factories.User(password=self.password)
        identity = {"login": user["name"], "password": self.password}
        assert (
            default_authenticate(identity).name
            == user["name"]
        )

    def test_fails_if_user_is_deleted(self):
        user = factories.User(password=self.password, state="deleted")
        identity = {"login": user["name"], "password": self.password}
        assert (
            default_authenticate(identity) is None
        )

    def test_fails_if_user_is_pending(self):
        user = factories.User(password=self.password, state="pending")
        identity = {"login": user["name"], "password": self.password}
        assert (
            default_authenticate(identity) is None
        )

    def test_fails_if_password_is_wrong(self):
        user = factories.User()
        identity = {"login": user["name"], "password": "wrong-password"}
        assert (
            default_authenticate(identity) is None
        )

    @pytest.mark.parametrize(
        "identity",
        [
            {},
            {"login": "some-user"},
            {"password": "some-password"},
        ],
    )
    def test_fails_if_received_no_login_or_pass(self, identity):
        assert (
            default_authenticate(identity) is None
        )

    def test_succeeds_if_email_and_password_are_correct(self):
        user = factories.User(password=self.password)
        identity = {"login": user["email"], "password": self.password}
        assert (
            default_authenticate(identity).name
            == user["name"]
        )
