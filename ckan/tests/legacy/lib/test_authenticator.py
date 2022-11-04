# encoding: utf-8

import ckan
import pytest
import ckan.lib.create_test_data as ctd
import ckan.lib.authenticator as authenticator

CreateTestData = ctd.CreateTestData


class TestUsernamePasswordAuthenticator(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        auth = authenticator.UsernamePasswordAuthenticator()
        self.authenticate = auth.authenticate

    def test_authenticate_succeeds_if_login_and_password_are_correct(self):
        environ = {}
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}

        username = self.authenticate(environ, identity)
        assert username == user.id + ",1", username

    def test_authenticate_fails_if_user_is_deleted(self):
        environ = {}
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}
        user.delete()

        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_is_pending(self):
        environ = {}
        password = "somepass"
        user = CreateTestData.create_user("a_user", **{"password": password})
        identity = {"login": user.name, "password": password}
        user.set_pending()

        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_password_is_wrong(self):
        environ = {}
        user = CreateTestData.create_user("a_user")
        identity = {"login": user.name, "password": "wrong-password"}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_no_login_or_pass(self):
        environ = {}
        identity = {}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_just_login(self):
        environ = {}
        identity = {"login": "some-user"}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_just_password(self):
        environ = {}
        identity = {"password": "some-password"}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_doesnt_exist(self):
        environ = {}
        identity = {"login": "inexistent-user"}
        assert self.authenticate(environ, identity) is None
